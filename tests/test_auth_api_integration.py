"""
Auth HTTP integration tests (PostgreSQL + migrations + JWT).

Uses the same DB URL rules as ``tests/integration_db.py`` (host-reachable URL).

Run: ``pytest tests/test_auth_api_integration.py -m integration -v``
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
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import update

from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]

JWT_INTEGRATION_KEY = "x" * 32


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
def _alembic_for_auth_api() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def auth_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "auth") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _assert_error_envelope(response, *, status_code: int, code: str | None = None) -> dict:
    assert response.status_code == status_code, response.text
    data = response.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    if code is not None:
        assert data["error"]["code"] == code
    return data


def _register(client: TestClient, email: str, password: str = "password123") -> dict:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test"},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _set_user_active(email: str, active: bool, monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        await session.execute(
            update(User).where(User.email == email).values(is_active=active)
        )
        await session.commit()
    await dispose_engine()
    get_settings.cache_clear()


def test_register_works(auth_client: TestClient) -> None:
    """Checklist (1): register returns user + tokens."""
    email = _unique_email("reg")
    data = _register(auth_client, email)
    assert data["user"]["email"] == email
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] >= 60


def test_login_works(auth_client: TestClient) -> None:
    """Checklist (2): login returns tokens for existing user."""
    email = _unique_email("login")
    password = "mySecurePass99"
    _register(auth_client, email, password)
    r = auth_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["user"]["email"] == email
    assert data["access_token"] and data["refresh_token"]


def test_register_duplicate_email_rejected(auth_client: TestClient) -> None:
    """Checklist (3): second register with same email → 409."""
    email = _unique_email("dup")
    _register(auth_client, email)
    r = auth_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "otherpass123", "full_name": "X"},
    )
    _assert_error_envelope(r, status_code=409, code="email_already_registered")


def test_login_invalid_password_rejected(auth_client: TestClient) -> None:
    """Checklist (4): wrong password → 401."""
    email = _unique_email("badpw")
    _register(auth_client, email, "correctHorseBattery99")
    r = auth_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong_password_here"},
    )
    data = _assert_error_envelope(r, status_code=401, code="invalid_credentials")
    assert data["error"].get("category") == "authentication"


def test_me_works_with_valid_access_token(auth_client: TestClient) -> None:
    """Checklist (5): Bearer access token returns profile."""
    email = _unique_email("me_ok")
    reg = _register(auth_client, email)
    token = reg["access_token"]
    r = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["email"] == email


def test_me_fails_without_token(auth_client: TestClient) -> None:
    """Checklist (6): missing Authorization → 401 (``CurrentUser``)."""
    r = auth_client.get("/api/v1/auth/me")
    _assert_error_envelope(r, status_code=401, code="not_authenticated")


def test_refresh_works_with_valid_refresh_token(auth_client: TestClient) -> None:
    """Checklist (7): refresh accepts refresh JWT and returns new pair."""
    email = _unique_email("refresh_ok")
    reg = _register(auth_client, email)
    r = auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": reg["refresh_token"]},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["access_token"] != reg["access_token"]
    assert data["refresh_token"] != reg["refresh_token"]
    assert data["token_type"] == "Bearer"


def test_refresh_old_token_rejected_after_rotation(auth_client: TestClient) -> None:
    email = _unique_email("rot_once")
    reg = _register(auth_client, email)
    old_rt = reg["refresh_token"]
    r1 = auth_client.post("/api/v1/auth/refresh", json={"refresh_token": old_rt})
    assert r1.status_code == 200, r1.text
    r2 = auth_client.post("/api/v1/auth/refresh", json={"refresh_token": old_rt})
    _assert_error_envelope(r2, status_code=401, code="refresh_token_reuse_detected")


def test_refresh_new_token_works_until_reuse_attack(auth_client: TestClient) -> None:
    email = _unique_email("rot_chain")
    reg = _register(auth_client, email)
    r1 = auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": reg["refresh_token"]},
    )
    assert r1.status_code == 200, r1.text
    rt_b = r1.json()["refresh_token"]
    r_ok = auth_client.post("/api/v1/auth/refresh", json={"refresh_token": rt_b})
    assert r_ok.status_code == 200, r_ok.text


def test_list_sessions_returns_active_rows(auth_client: TestClient) -> None:
    email = _unique_email("sessions")
    reg = _register(auth_client, email)
    r = auth_client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {reg['access_token']}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert len(body["items"]) >= 1
    assert body["items"][0]["user_id"] == reg["user"]["id"]


def test_logout_current_revokes_refresh_session(auth_client: TestClient) -> None:
    email = _unique_email("logout_cur")
    reg = _register(auth_client, email)
    r = auth_client.post(
        "/api/v1/auth/logout-current",
        json={"refresh_token": reg["refresh_token"]},
    )
    assert r.status_code == 204, r.text
    r2 = auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": reg["refresh_token"]},
    )
    _assert_error_envelope(r2, status_code=401, code="refresh_token_revoked")


def test_logout_all_revokes_every_session(auth_client: TestClient) -> None:
    email = _unique_email("logout_all")
    password = "p4ssword!!"
    reg = _register(auth_client, email, password)
    login2 = auth_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login2.status_code == 200, login2.text
    r = auth_client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {reg['access_token']}"},
    )
    assert r.status_code == 204, r.text
    for rt in (reg["refresh_token"], login2.json()["refresh_token"]):
        ref = auth_client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
        _assert_error_envelope(ref, status_code=401, code="refresh_token_revoked")


def test_refresh_fails_with_access_token(auth_client: TestClient) -> None:
    """Checklist (8): access JWT is wrong type for refresh → 401."""
    email = _unique_email("refresh_bad")
    reg = _register(auth_client, email)
    r = auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": reg["access_token"]},
    )
    _assert_error_envelope(r, status_code=401, code="invalid_refresh_token")


def test_inactive_user_cannot_login(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch, live_db_url: str
) -> None:
    """Checklist (9): disabled account cannot obtain tokens via login."""
    email = _unique_email("inactive")
    password = "stillSecret123"
    _register(auth_client, email, password)
    asyncio.run(_set_user_active(email, False, monkeypatch, live_db_url))

    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())

    with TestClient(app) as client:
        r = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
    _assert_error_envelope(r, status_code=403, code="inactive_user")

    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def test_dependency_optional_session_unauthenticated(auth_client: TestClient) -> None:
    """``CurrentUserOptional``: no header → authenticated false."""
    r = auth_client.get("/api/v1/auth/session")
    assert r.status_code == 200
    assert r.json() == {"authenticated": False}


def test_dependency_optional_session_authenticated(auth_client: TestClient) -> None:
    """``CurrentUserOptional``: valid access token → authenticated true."""
    email = _unique_email("sess")
    reg = _register(auth_client, email)
    r = auth_client.get(
        "/api/v1/auth/session",
        headers={"Authorization": f"Bearer {reg['access_token']}"},
    )
    assert r.status_code == 200
    assert r.json() == {"authenticated": True}


def test_dependency_required_me_rejects_malformed_authorization(auth_client: TestClient) -> None:
    """``CurrentUser`` (via ``/me``): garbage bearer → 401."""
    r = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    _assert_error_envelope(r, status_code=401, code="not_authenticated")
