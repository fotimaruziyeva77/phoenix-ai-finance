"""
RBAC HTTP integration tests (PostgreSQL + real JWT).

Verifies customer_admin owner routes, superadmin-only admin routes, and no cross-tenant bot access
for superadmin on owner-scoped APIs.

Run: ``pytest tests/test_rbac_authz_integration.py -m integration -v``
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
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.user import User
from app.services.audit_service import TENANT_ACTION_SUPERADMIN_INSPECT
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_INTEGRATION_KEY = "y" * 32


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
def _alembic_for_rbac_authz() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def rbac_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "rbac") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register(client: TestClient, email: str, password: str = "password123") -> dict:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "RBAC"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def _tenant_inspect_audit_count(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
    *,
    tenant_id: uuid.UUID,
) -> int:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        n = await session.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.entity_id == tenant_id,
                AuditLog.action == TENANT_ACTION_SUPERADMIN_INSPECT,
            ),
        )
        return int(n or 0)


async def _last_tenant_inspect_actor(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
    *,
    tenant_id: uuid.UUID,
) -> uuid.UUID | None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        return await session.scalar(
            select(AuditLog.actor_user_id)
            .where(
                AuditLog.entity_id == tenant_id,
                AuditLog.action == TENANT_ACTION_SUPERADMIN_INSPECT,
            )
            .order_by(AuditLog.created_at.desc())
            .limit(1),
        )


async def _promote_to_superadmin(user_id, live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        await session.execute(update(User).where(User.id == user_id).values(role=UserRole.superadmin))
        await session.commit()


def test_customer_admin_me_and_list_bots_work(rbac_client: TestClient) -> None:
    reg = _register(rbac_client, _unique_email("ca"))
    token = reg["access_token"]
    r_me = rbac_client.get("/api/v1/auth/me", headers=_auth_headers(token))
    assert r_me.status_code == 200
    assert r_me.json()["role"] == "customer_admin"

    r_list = rbac_client.get("/api/v1/bots", headers=_auth_headers(token))
    assert r_list.status_code == 200
    assert "items" in r_list.json()


def test_customer_admin_blocked_from_admin_platform_session(rbac_client: TestClient) -> None:
    reg = _register(rbac_client, _unique_email("ca_admin"))
    token = reg["access_token"]
    r = rbac_client.get("/api/v1/admin/platform/session", headers=_auth_headers(token))
    assert r.status_code == 403
    assert r.json()["error"]["message"] == "Superadmin access required."


def test_superadmin_admin_platform_session_ok(
    rbac_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reg = _register(rbac_client, _unique_email("sa"))
    token = reg["access_token"]
    user_id = uuid.UUID(reg["user"]["id"])
    asyncio.run(_promote_to_superadmin(user_id, live_db_url, monkeypatch))

    r = rbac_client.get("/api/v1/admin/platform/session", headers=_auth_headers(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "superadmin"
    assert body["user_id"] == str(user_id)


def test_superadmin_cannot_get_other_tenants_bot_via_owner_scoped_route(
    rbac_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_reg = _register(rbac_client, _unique_email("owner"))
    owner_token = owner_reg["access_token"]
    create = rbac_client.post(
        "/api/v1/bots",
        headers=_auth_headers(owner_token),
        json={
            "name": "Foreign Bot",
            "niche_id": "generic",
            "goal_type": "sales",
        },
    )
    assert create.status_code == 201, create.text
    bot_id = create.json()["id"]

    other_reg = _register(rbac_client, _unique_email("other"))
    other_token = other_reg["access_token"]
    other_id = uuid.UUID(other_reg["user"]["id"])
    asyncio.run(_promote_to_superadmin(other_id, live_db_url, monkeypatch))

    r = rbac_client.get(f"/api/v1/bots/{bot_id}", headers=_auth_headers(other_token))
    assert r.status_code == 403, r.text
    assert r.json()["error"]["code"] == "forbidden"


def test_customer_admin_blocked_from_tenant_inspection(rbac_client: TestClient) -> None:
    reg = _register(rbac_client, _unique_email("inspect_ca"))
    token = reg["access_token"]
    tid = reg["user"]["id"]
    r = rbac_client.get(f"/api/v1/admin/tenants/{tid}/inspection", headers=_auth_headers(token))
    assert r.status_code == 403


def test_superadmin_tenant_inspection_ok_and_audited(
    rbac_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _register(rbac_client, _unique_email("inspect_owner"))
    owner_id = uuid.UUID(owner["user"]["id"])
    sa_reg = _register(rbac_client, _unique_email("inspect_sa"))
    sa_token = sa_reg["access_token"]
    sa_id = uuid.UUID(sa_reg["user"]["id"])
    asyncio.run(_promote_to_superadmin(sa_id, live_db_url, monkeypatch))

    before = asyncio.run(_tenant_inspect_audit_count(live_db_url, monkeypatch, tenant_id=owner_id))
    r = rbac_client.get(
        f"/api/v1/admin/tenants/{owner_id}/inspection",
        headers=_auth_headers(sa_token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenant_user_id"] == str(owner_id)
    assert body["summary"]["id"] == str(owner_id)
    assert "bots" in body and isinstance(body["bots"], list)
    assert "channels" in body and isinstance(body["channels"], list)
    assert body["lead_count"] == 0
    assert "ai_usage" in body
    assert "recent_ai_failures" in body
    after = asyncio.run(_tenant_inspect_audit_count(live_db_url, monkeypatch, tenant_id=owner_id))
    assert after == before + 1
    assert asyncio.run(_last_tenant_inspect_actor(live_db_url, monkeypatch, tenant_id=owner_id)) == sa_id


def test_superadmin_tenant_inspection_404_does_not_write_audit(
    rbac_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sa_reg = _register(rbac_client, _unique_email("inspect_sa404"))
    sa_token = sa_reg["access_token"]
    sa_id = uuid.UUID(sa_reg["user"]["id"])
    asyncio.run(_promote_to_superadmin(sa_id, live_db_url, monkeypatch))
    phantom = uuid.uuid4()
    before = asyncio.run(_tenant_inspect_audit_count(live_db_url, monkeypatch, tenant_id=phantom))
    r = rbac_client.get(
        f"/api/v1/admin/tenants/{phantom}/inspection",
        headers=_auth_headers(sa_token),
    )
    assert r.status_code == 404
    after = asyncio.run(_tenant_inspect_audit_count(live_db_url, monkeypatch, tenant_id=phantom))
    assert after == before


def test_owner_customer_admin_can_get_own_bot(rbac_client: TestClient) -> None:
    """Sanity: same bot id succeeds for the owning customer_admin."""
    owner_reg = _register(rbac_client, _unique_email("owner2"))
    owner_token = owner_reg["access_token"]
    create = rbac_client.post(
        "/api/v1/bots",
        headers=_auth_headers(owner_token),
        json={
            "name": "Mine",
            "niche_id": "generic",
            "goal_type": "sales",
        },
    )
    assert create.status_code == 201, create.text
    bot_id = create.json()["id"]

    r = rbac_client.get(f"/api/v1/bots/{bot_id}", headers=_auth_headers(owner_token))
    assert r.status_code == 200, r.text
    assert r.json()["id"] == bot_id
