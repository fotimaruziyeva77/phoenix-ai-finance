"""
Superadmin platform overview API integration tests (PostgreSQL + JWT).

Run: ``pytest tests/test_platform_admin_overview_integration.py -m integration -v``
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.main import app
from app.models.enums import UserRole
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import update

from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_ADMIN_OVERVIEW_KEY = "w" * 32

_SECRET_SUBSTRINGS = (
    "password_hash",
    "bot_token",
    "webhook_secret",
    "refresh_token",
    "client_secret",
    "private_key",
    "fernet",
)


def _integration_db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _integration_db_url(),
        reason=(
            "Set TEST_DATABASE_URL or host-reachable DATABASE_URL "
            "(not @postgres: from host)."
        ),
    ),
]


def _alembic_upgrade_head(url: str) -> None:
    import os

    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        command.upgrade(cfg, "head")
    finally:
        if prev is not None:
            os.environ["DATABASE_URL"] = prev
        else:
            os.environ.pop("DATABASE_URL", None)
        get_settings.cache_clear()


@pytest.fixture(scope="module", autouse=True)
def _alembic_for_platform_admin_overview() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def admin_overview_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_ADMIN_OVERVIEW_KEY)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "adm") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register(client: TestClient, email: str, password: str = "password123") -> dict:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Admin Overview"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def _promote_to_superadmin(user_id: uuid.UUID, live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_ADMIN_OVERVIEW_KEY)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        await session.execute(update(User).where(User.id == user_id).values(role=UserRole.superadmin))
        await session.commit()


def _assert_no_secret_leak(blob: str) -> None:
    lower = blob.lower()
    for s in _SECRET_SUBSTRINGS:
        assert s not in lower, f"response leaked forbidden substring {s!r}"


def test_customer_admin_blocked_from_admin_overview(admin_overview_client: TestClient) -> None:
    reg = _register(admin_overview_client, _unique_email("cust"))
    token = reg["access_token"]
    r = admin_overview_client.get("/api/v1/admin/users", headers=_auth_headers(token))
    assert r.status_code == 403
    _assert_no_secret_leak(r.text)


def test_superadmin_can_list_users_and_detail(
    admin_overview_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("owner")
    owner_reg = _register(admin_overview_client, owner_email)
    owner_id = uuid.UUID(owner_reg["user"]["id"])
    owner_token = owner_reg["access_token"]

    create = admin_overview_client.post(
        "/api/v1/bots",
        headers=_auth_headers(owner_token),
        json={"name": "Overview Bot", "niche_id": "generic", "goal_type": "sales"},
    )
    assert create.status_code == 201, create.text

    sa_reg = _register(admin_overview_client, _unique_email("super"))
    sa_token = sa_reg["access_token"]
    sa_id = uuid.UUID(sa_reg["user"]["id"])
    asyncio.run(_promote_to_superadmin(sa_id, live_db_url, monkeypatch))

    r_list = admin_overview_client.get("/api/v1/admin/users", headers=_auth_headers(sa_token))
    assert r_list.status_code == 200, r_list.text
    _assert_no_secret_leak(r_list.text)
    body = r_list.json()
    assert body["total"] >= 2
    emails = {item["email"] for item in body["items"]}
    assert owner_email in emails

    r_one = admin_overview_client.get(
        f"/api/v1/admin/users/{owner_id}",
        headers=_auth_headers(sa_token),
    )
    assert r_one.status_code == 200, r_one.text
    _assert_no_secret_leak(r_one.text)
    detail = r_one.json()
    assert detail["email"] == owner_email
    assert detail["id"] == str(owner_id)
    assert "has_password" in detail
    assert detail["bot_count"] >= 1
    assert isinstance(detail["oauth_providers"], list)


def test_superadmin_can_list_bots_and_detail(
    admin_overview_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("botowner")
    owner_reg = _register(admin_overview_client, owner_email)
    owner_token = owner_reg["access_token"]

    create = admin_overview_client.post(
        "/api/v1/bots",
        headers=_auth_headers(owner_token),
        json={"name": "List Me Bot", "niche_id": "retail", "goal_type": "faq"},
    )
    assert create.status_code == 201, create.text
    bot_id = create.json()["id"]

    sa_reg = _register(admin_overview_client, _unique_email("sabot"))
    sa_token = sa_reg["access_token"]
    sa_id = uuid.UUID(sa_reg["user"]["id"])
    asyncio.run(_promote_to_superadmin(sa_id, live_db_url, monkeypatch))

    r_list = admin_overview_client.get("/api/v1/admin/bots", headers=_auth_headers(sa_token))
    assert r_list.status_code == 200, r_list.text
    _assert_no_secret_leak(r_list.text)
    lst = r_list.json()
    assert lst["total"] >= 1
    ids = {item["id"] for item in lst["items"]}
    assert bot_id in ids
    match = next(x for x in lst["items"] if x["id"] == bot_id)
    assert match["owner_email"] == owner_email
    assert match["niche_id"] == "retail"
    assert "widget_configured" in match
    assert "telegram_connected" in match

    r_one = admin_overview_client.get(
        f"/api/v1/admin/bots/{bot_id}",
        headers=_auth_headers(sa_token),
    )
    assert r_one.status_code == 200, r_one.text
    _assert_no_secret_leak(r_one.text)
    one = r_one.json()
    assert one["id"] == bot_id
    assert one["owner_email"] == owner_email


def test_superadmin_user_detail_404(
    admin_overview_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sa_reg = _register(admin_overview_client, _unique_email("sa404"))
    sa_token = sa_reg["access_token"]
    sa_id = uuid.UUID(sa_reg["user"]["id"])
    asyncio.run(_promote_to_superadmin(sa_id, live_db_url, monkeypatch))
    missing = uuid.uuid4()
    r = admin_overview_client.get(f"/api/v1/admin/users/{missing}", headers=_auth_headers(sa_token))
    assert r.status_code == 404


def test_superadmin_filters_role_and_niche(
    admin_overview_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _register(admin_overview_client, _unique_email("ca_only"))
    sa_reg = _register(admin_overview_client, _unique_email("safilt"))
    sa_token = sa_reg["access_token"]
    sa_id = uuid.UUID(sa_reg["user"]["id"])
    asyncio.run(_promote_to_superadmin(sa_id, live_db_url, monkeypatch))

    r = admin_overview_client.get(
        "/api/v1/admin/users",
        headers=_auth_headers(sa_token),
        params={"role": "customer_admin"},
    )
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["role"] == "customer_admin"

    niche_owner = _register(admin_overview_client, _unique_email("niche_o"))
    ot = niche_owner["access_token"]
    admin_overview_client.post(
        "/api/v1/bots",
        headers=_auth_headers(ot),
        json={"name": "Niche Bot", "niche_id": "education_niche_test", "goal_type": "support"},
    )

    r2 = admin_overview_client.get(
        "/api/v1/admin/bots",
        headers=_auth_headers(sa_token),
        params={"niche_id": "education_niche_test"},
    )
    assert r2.status_code == 200
    for item in r2.json()["items"]:
        assert item["niche_id"] == "education_niche_test"


def test_json_shape_excludes_sensitive_keys(
    admin_overview_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Walk JSON keys to ensure common secret field names never appear."""
    owner_reg = _register(admin_overview_client, _unique_email("walk"))
    owner_token = owner_reg["access_token"]
    admin_overview_client.post(
        "/api/v1/bots",
        headers=_auth_headers(owner_token),
        json={"name": "Walk Bot", "niche_id": "generic", "goal_type": "sales"},
    )

    sa_reg = _register(admin_overview_client, _unique_email("walk_sa"))
    sa_token = sa_reg["access_token"]
    sa_id = uuid.UUID(sa_reg["user"]["id"])
    asyncio.run(_promote_to_superadmin(sa_id, live_db_url, monkeypatch))

    forbidden_keys = frozenset(
        {
            "password_hash",
            "bot_token_encrypted",
            "webhook_secret_token_encrypted",
            "access_token",
            "refresh_token",
            "public_widget_key",
        }
    )

    def walk(obj: object, path: str) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert k not in forbidden_keys, f"unexpected key at {path}.{k}"
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")

    for url in (
        "/api/v1/admin/users",
        f"/api/v1/admin/users/{owner_reg['user']['id']}",
        "/api/v1/admin/bots",
    ):
        r = admin_overview_client.get(url, headers=_auth_headers(sa_token))
        assert r.status_code == 200, r.text
        walk(r.json(), url)

    bot_list = admin_overview_client.get("/api/v1/admin/bots", headers=_auth_headers(sa_token)).json()
    if bot_list["items"]:
        bid = bot_list["items"][0]["id"]
        r2 = admin_overview_client.get(f"/api/v1/admin/bots/{bid}", headers=_auth_headers(sa_token))
        assert r2.status_code == 200
        walk(r2.json(), f"/bots/{bid}")
