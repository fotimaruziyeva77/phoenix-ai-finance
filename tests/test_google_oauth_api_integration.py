"""
Google OAuth HTTP flow with mocked Google token + userinfo calls (real PostgreSQL).

Run: ``pytest tests/test_google_oauth_api_integration.py -m integration -v``
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from app.api import deps as api_deps
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.integrations.oauth_state import create_google_oauth_state
from app.main import app
from app.models.enums import OAuthProvider
from app.models.user import OAuthAccount, User
from app.services.auth_exceptions import GoogleOAuthProviderError
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.integration_db import integration_database_url
from tests.test_auth_api_integration import (
    JWT_INTEGRATION_KEY,
    _alembic_upgrade_head,
    _register,
    _unique_email,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not integration_database_url(),
        reason=(
            "Set TEST_DATABASE_URL or host-reachable DATABASE_URL "
            "(not @postgres: from host)."
        ),
    ),
]


@pytest.fixture(scope="module", autouse=True)
def _alembic_for_google_oauth() -> None:
    url = integration_database_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = integration_database_url()
    assert u is not None
    return u


def _reset_oauth_store() -> None:
    api_deps._oauth_exchange_store = None


@pytest.fixture
def google_oauth_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-google-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-google-client-secret")
    monkeypatch.setenv(
        "GOOGLE_OAUTH_REDIRECT_URI",
        "http://127.0.0.1:8000/api/v1/auth/google/callback",
    )
    monkeypatch.setenv("FRONTEND_OAUTH_REDIRECT_URL", "http://localhost:3000/auth/callback")
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    _reset_oauth_store()
    with TestClient(app, follow_redirects=False) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()
    _reset_oauth_store()


def _mock_google_success(
    *,
    sub: str,
    email: str,
    email_verified: bool = True,
    name: str | None = "OAuth User",
) -> tuple[AsyncMock, AsyncMock]:
    exchange = AsyncMock(return_value={"access_token": "mock-google-access-token"})
    userinfo = AsyncMock(
        return_value={
            "sub": sub,
            "email": email,
            "email_verified": email_verified,
            "name": name,
        }
    )
    return exchange, userinfo


def _callback(
    client: TestClient,
    *,
    code: str | None = "google-auth-code",
    state: str | None = None,
    error: str | None = None,
):
    params: dict[str, str] = {}
    if code is not None:
        params["code"] = code
    if state is not None:
        params["state"] = state
    if error is not None:
        params["error"] = error
    return client.get("/api/v1/auth/google/callback", params=params)


def _parse_redirect_location(response) -> tuple[str, dict[str, list[str]]]:
    assert response.status_code == 302, response.text
    loc = response.headers["location"]
    parsed = urlparse(loc)
    return loc, parse_qs(parsed.query)


def _exchange_from_callback_response(client: TestClient, response) -> dict:
    _, qs = _parse_redirect_location(response)
    codes = qs.get("oauth_exchange_code")
    assert codes, qs
    r = client.post("/api/v1/auth/oauth/exchange", json={"exchange_code": codes[0]})
    assert r.status_code == 200, r.text
    return r.json()


async def _count_users_by_email(email: str, live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        result = await session.execute(select(func.count()).select_from(User).where(User.email == email))
        return int(result.scalar_one())


async def _count_oauth_google_by_sub(sub: str, live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        result = await session.execute(
            select(func.count()).select_from(OAuthAccount).where(
                OAuthAccount.provider == OAuthProvider.google,
                OAuthAccount.provider_user_id == sub,
            )
        )
        return int(result.scalar_one())


def test_oauth_callback_valid_payload_creates_user_and_exchange_returns_tokens(
    google_oauth_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid code + state + verified email → one user, JWT session via exchange."""
    email = _unique_email("go_new")
    sub = f"google-sub-{uuid.uuid4().hex}"
    get_settings.cache_clear()
    state = create_google_oauth_state(get_settings())
    ex, ui = _mock_google_success(sub=sub, email=email)

    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = _callback(google_oauth_client, state=state)

    data = _exchange_from_callback_response(google_oauth_client, r)
    assert data["user"]["email"] == email
    assert data["access_token"]
    assert data["refresh_token"]

    n_users = asyncio.run(_count_users_by_email(email, live_db_url, monkeypatch))
    n_links = asyncio.run(_count_oauth_google_by_sub(sub, live_db_url, monkeypatch))
    assert n_users == 1
    assert n_links == 1
    ex.assert_awaited_once()
    ui.assert_awaited_once()


def test_oauth_callback_existing_email_password_user_links_google(
    google_oauth_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same email as existing account → link OAuthAccount, no second user."""
    email = _unique_email("go_link")
    password = "localPassword123"
    reg = _register(google_oauth_client, email, password)
    user_id_before = reg["user"]["id"]

    sub = f"google-sub-{uuid.uuid4().hex}"
    get_settings.cache_clear()
    state = create_google_oauth_state(get_settings())
    ex, ui = _mock_google_success(sub=sub, email=email)

    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = _callback(google_oauth_client, state=state)

    data = _exchange_from_callback_response(google_oauth_client, r)
    assert data["user"]["id"] == user_id_before
    assert data["user"]["email"] == email

    n_users = asyncio.run(_count_users_by_email(email, live_db_url, monkeypatch))
    n_links = asyncio.run(_count_oauth_google_by_sub(sub, live_db_url, monkeypatch))
    assert n_users == 1
    assert n_links == 1


def test_oauth_duplicate_provider_login_no_extra_users_or_oauth_rows(
    google_oauth_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Second callback with same Google sub reuses account (no duplicate users/links)."""
    email = _unique_email("go_dup")
    sub = f"google-sub-{uuid.uuid4().hex}"
    get_settings.cache_clear()

    def run_flow() -> dict:
        state = create_google_oauth_state(get_settings())
        ex, ui = _mock_google_success(sub=sub, email=email)
        with (
            patch("app.services.google_oauth_service.exchange_authorization_code", ex),
            patch("app.services.google_oauth_service.fetch_userinfo", ui),
        ):
            r = _callback(google_oauth_client, state=state)
        return _exchange_from_callback_response(google_oauth_client, r)

    d1 = run_flow()
    d2 = run_flow()

    assert d1["user"]["id"] == d2["user"]["id"]
    n_users = asyncio.run(_count_users_by_email(email, live_db_url, monkeypatch))
    n_links = asyncio.run(_count_oauth_google_by_sub(sub, live_db_url, monkeypatch))
    assert n_users == 1
    assert n_links == 1


def test_oauth_callback_invalid_state_rejected(google_oauth_client: TestClient) -> None:
    """Tampered or wrong state → redirect with google_oauth_invalid_state (no session)."""
    ex, ui = _mock_google_success(sub="sub", email="x@y.com")
    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = _callback(google_oauth_client, state="not-a-valid-jwt", code="any")

    loc, qs = _parse_redirect_location(r)
    assert "localhost:3000" in loc
    assert qs.get("oauth_error") == ["google_oauth_invalid_state"]
    assert "oauth_exchange_code" not in qs
    ex.assert_not_called()
    ui.assert_not_called()


def test_oauth_callback_malformed_missing_code(google_oauth_client: TestClient) -> None:
    get_settings.cache_clear()
    state = create_google_oauth_state(get_settings())
    ex, ui = _mock_google_success(sub="s", email="a@b.com")
    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = _callback(google_oauth_client, code="", state=state)

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["google_oauth_missing_code"]
    ex.assert_not_called()


def test_oauth_callback_malformed_missing_state(google_oauth_client: TestClient) -> None:
    ex, ui = _mock_google_success(sub="s", email="a@b.com")
    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = _callback(google_oauth_client, state=None, code="c")

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["google_oauth_invalid_state"]
    ex.assert_not_called()


def test_oauth_callback_provider_access_denied(google_oauth_client: TestClient) -> None:
    ex, ui = _mock_google_success(sub="s", email="a@b.com")
    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = _callback(google_oauth_client, error="access_denied", state=None, code=None)

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["google_oauth_denied"]
    ex.assert_not_called()


def test_oauth_callback_token_exchange_failure_redirects(
    google_oauth_client: TestClient,
) -> None:
    get_settings.cache_clear()
    state = create_google_oauth_state(get_settings())
    ex = AsyncMock(side_effect=GoogleOAuthProviderError("fail"))
    ui = AsyncMock()

    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = _callback(google_oauth_client, state=state)

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["google_token_exchange_failed"]
    ui.assert_not_called()


def test_oauth_email_not_verified_redirects(
    google_oauth_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = _unique_email("go_unverified")
    get_settings.cache_clear()
    state = create_google_oauth_state(get_settings())
    ex, ui = _mock_google_success(sub=f"sub-{uuid.uuid4().hex}", email=email, email_verified=False)

    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = _callback(google_oauth_client, state=state)

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["google_email_not_verified"]
    n_users = asyncio.run(_count_users_by_email(email, live_db_url, monkeypatch))
    assert n_users == 0


def test_oauth_link_conflict_when_email_already_has_different_google_sub(
    google_oauth_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Email already linked to Google sub A cannot accept callback for sub B."""
    email = _unique_email("go_conflict")
    sub_a = f"google-a-{uuid.uuid4().hex}"
    sub_b = f"google-b-{uuid.uuid4().hex}"

    def run(*, sub: str):
        get_settings.cache_clear()
        state = create_google_oauth_state(get_settings())
        ex, ui = _mock_google_success(sub=sub, email=email)
        with (
            patch("app.services.google_oauth_service.exchange_authorization_code", ex),
            patch("app.services.google_oauth_service.fetch_userinfo", ui),
        ):
            return _callback(google_oauth_client, state=state)

    r_ok = run(sub=sub_a)
    _exchange_from_callback_response(google_oauth_client, r_ok)

    r_fail = run(sub=sub_b)
    _, qs = _parse_redirect_location(r_fail)
    assert qs.get("oauth_error") == ["google_oauth_link_conflict"]

    n_users = asyncio.run(_count_users_by_email(email, live_db_url, monkeypatch))
    n_a = asyncio.run(_count_oauth_google_by_sub(sub_a, live_db_url, monkeypatch))
    n_b = asyncio.run(_count_oauth_google_by_sub(sub_b, live_db_url, monkeypatch))
    assert n_users == 1
    assert n_a == 1
    assert n_b == 0


def test_oauth_exchange_code_single_use(
    google_oauth_client: TestClient,
) -> None:
    """Second POST with the same exchange code must fail (401)."""
    email = _unique_email("go_once")
    sub = f"google-sub-{uuid.uuid4().hex}"
    get_settings.cache_clear()
    state = create_google_oauth_state(get_settings())
    ex, ui = _mock_google_success(sub=sub, email=email)

    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = _callback(google_oauth_client, state=state)

    _, qs = _parse_redirect_location(r)
    code = qs["oauth_exchange_code"][0]
    r1 = google_oauth_client.post("/api/v1/auth/oauth/exchange", json={"exchange_code": code})
    r2 = google_oauth_client.post("/api/v1/auth/oauth/exchange", json={"exchange_code": code})
    assert r1.status_code == 200
    assert r2.status_code == 401
    assert r2.json()["error"]["code"] == "oauth_exchange_invalid"


def test_oauth_token_response_without_access_token_redirects(
    google_oauth_client: TestClient,
) -> None:
    get_settings.cache_clear()
    state = create_google_oauth_state(get_settings())
    ex = AsyncMock(return_value={"id_token": "only"})
    ui = AsyncMock()

    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = _callback(google_oauth_client, state=state)

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["google_token_exchange_failed"]
    ui.assert_not_called()


def test_oauth_userinfo_missing_sub_redirects(google_oauth_client: TestClient) -> None:
    email = _unique_email("go_nosub")
    get_settings.cache_clear()
    state = create_google_oauth_state(get_settings())
    ex, ui = _mock_google_success(sub="placeholder", email=email)
    ui.return_value = {"email": email, "email_verified": True}

    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = _callback(google_oauth_client, state=state)

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["google_oauth_provider_error"]
