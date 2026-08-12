"""
Google/GitHub OAuth callback → redirect → one-time exchange (real app + Postgres).

Provider token/userinfo HTTP is stubbed (``AsyncMock``); routing, state validation, DB linking,
and JWT issuance run unmocked in-process.
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

pytestmark = pytest.mark.integration

from app.api import deps as api_deps
from app.core.config import get_settings
from app.core.db import dispose_engine
from app.integrations.oauth_state import create_github_oauth_state, create_google_oauth_state
from app.main import app
from app.models.enums import OAuthProvider
from app.models.user import OAuthAccount, User
from app.services.auth_exceptions import GithubOAuthProviderError, GoogleOAuthProviderError

from tests.integration.auth_setup import (
    JWT_INTEGRATION_KEY,
    apply_auth_test_env,
    register_user,
    unique_email,
)
from tests.integration.oauth_flow_helpers import (
    exchange_oauth_code,
    github_callback,
    google_callback,
    mock_github_provider,
    mock_google_provider,
    parse_oauth_redirect,
    patch_github,
)


def _reset_oauth_store() -> None:
    api_deps._oauth_exchange_store = None


@pytest.fixture
def oauth_http_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    apply_auth_test_env(
        monkeypatch,
        live_db_url,
        extra={
            "GOOGLE_CLIENT_ID": "test-google-client-id",
            "GOOGLE_CLIENT_SECRET": "test-google-client-secret",
            "GOOGLE_OAUTH_REDIRECT_URI": "http://127.0.0.1:8000/api/v1/auth/google/callback",
            "GITHUB_CLIENT_ID": "test-github-client-id",
            "GITHUB_CLIENT_SECRET": "test-github-client-secret",
            "GITHUB_OAUTH_REDIRECT_URI": "http://127.0.0.1:8000/api/v1/auth/github/callback",
            "FRONTEND_OAUTH_REDIRECT_URL": "http://localhost:3000/auth/callback",
        },
    )
    _reset_oauth_store()
    with TestClient(app, follow_redirects=False) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()
    _reset_oauth_store()


async def _count_users_by_email(email: str, live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> int:
    from app.core.config import get_settings as gs
    from app.core.db import get_session_maker

    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    gs.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        result = await session.execute(select(func.count()).select_from(User).where(User.email == email))
        return int(result.scalar_one())


async def _count_oauth(
    *,
    provider: OAuthProvider,
    sub: str,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> int:
    from app.core.config import get_settings as gs
    from app.core.db import get_session_maker

    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    gs.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        result = await session.execute(
            select(func.count()).select_from(OAuthAccount).where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == sub,
            )
        )
        return int(result.scalar_one())


# --- Google ---


def test_google_oauth_callback_success_creates_user_and_exchange_returns_tokens(
    oauth_http_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = unique_email("go_ok")
    sub = f"google-sub-{uuid.uuid4().hex}"
    get_settings.cache_clear()
    state = create_google_oauth_state(get_settings())
    ex, ui = mock_google_provider(sub=sub, email=email)
    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = google_callback(oauth_http_client, state=state)
    data = exchange_oauth_code(oauth_http_client, r)
    assert data["user"]["email"] == email
    assert data["access_token"]
    assert data["refresh_token"]
    assert asyncio.run(_count_users_by_email(email, live_db_url, monkeypatch)) == 1
    assert asyncio.run(_count_oauth(provider=OAuthProvider.google, sub=sub, live_db_url=live_db_url, monkeypatch=monkeypatch)) == 1


def test_google_oauth_callback_failure_invalid_state(
    oauth_http_client: TestClient,
) -> None:
    ex, ui = mock_google_provider(sub="s", email="a@b.com")
    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = google_callback(oauth_http_client, state="not-a-valid-jwt", code="any")
    loc, qs = parse_oauth_redirect(r)
    assert "localhost:3000" in loc
    assert qs.get("oauth_error") == ["google_oauth_invalid_state"]
    assert "oauth_exchange_code" not in qs
    ex.assert_not_called()
    ui.assert_not_called()


def test_google_oauth_callback_failure_email_not_verified(
    oauth_http_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = unique_email("go_unverified")
    get_settings.cache_clear()
    state = create_google_oauth_state(get_settings())
    ex, ui = mock_google_provider(sub=f"sub-{uuid.uuid4().hex}", email=email, email_verified=False)
    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = google_callback(oauth_http_client, state=state)
    _, qs = parse_oauth_redirect(r)
    assert qs.get("oauth_error") == ["google_email_not_verified"]
    assert asyncio.run(_count_users_by_email(email, live_db_url, monkeypatch)) == 0


def test_google_oauth_callback_failure_token_exchange_error(
    oauth_http_client: TestClient,
) -> None:
    get_settings.cache_clear()
    state = create_google_oauth_state(get_settings())
    ex = AsyncMock(side_effect=GoogleOAuthProviderError("fail"))
    ui = AsyncMock()
    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = google_callback(oauth_http_client, state=state)
    _, qs = parse_oauth_redirect(r)
    assert qs.get("oauth_error") == ["google_token_exchange_failed"]
    ui.assert_not_called()


# --- GitHub ---


def test_github_oauth_callback_success_creates_user_and_exchange_returns_tokens(
    oauth_http_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = unique_email("gh_ok")
    gid = uuid.uuid4().int % 1_000_000_000
    sub = str(gid)
    get_settings.cache_clear()
    state = create_github_oauth_state(get_settings())
    ex, u, em = mock_github_provider(github_id=gid, email=email)
    with patch_github(ex, u, em):
        r = github_callback(oauth_http_client, state=state)
    data = exchange_oauth_code(oauth_http_client, r)
    assert data["user"]["email"] == email
    assert data["access_token"]
    assert data["refresh_token"]
    assert asyncio.run(_count_users_by_email(email, live_db_url, monkeypatch)) == 1
    assert asyncio.run(_count_oauth(provider=OAuthProvider.github, sub=sub, live_db_url=live_db_url, monkeypatch=monkeypatch)) == 1


def test_github_oauth_callback_failure_invalid_state(
    oauth_http_client: TestClient,
) -> None:
    ex, u, em = mock_github_provider(github_id=1, email="x@y.com")
    with patch_github(ex, u, em):
        r = github_callback(oauth_http_client, state="not-a-valid-jwt", code="any")
    loc, qs = parse_oauth_redirect(r)
    assert "localhost:3000" in loc
    assert qs.get("oauth_error") == ["github_oauth_invalid_state"]
    assert "oauth_exchange_code" not in qs
    ex.assert_not_called()
    u.assert_not_called()
    em.assert_not_called()


def test_github_oauth_callback_failure_no_verified_email(
    oauth_http_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = unique_email("gh_no_email")
    get_settings.cache_clear()
    state = create_github_oauth_state(get_settings())
    ex, u, em = mock_github_provider(
        github_id=uuid.uuid4().int % 1_000_000_000,
        email=probe,
        email_rows=[],
    )
    with patch_github(ex, u, em):
        r = github_callback(oauth_http_client, state=state)
    _, qs = parse_oauth_redirect(r)
    assert qs.get("oauth_error") == ["github_oauth_email_unavailable"]
    assert asyncio.run(_count_users_by_email(probe, live_db_url, monkeypatch)) == 0


def test_github_oauth_callback_failure_token_exchange_error(
    oauth_http_client: TestClient,
) -> None:
    get_settings.cache_clear()
    state = create_github_oauth_state(get_settings())
    ex = AsyncMock(side_effect=GithubOAuthProviderError("fail"))
    u = AsyncMock()
    em = AsyncMock()
    with patch_github(ex, u, em):
        r = github_callback(oauth_http_client, state=state)
    _, qs = parse_oauth_redirect(r)
    assert qs.get("oauth_error") == ["github_token_exchange_failed"]
    u.assert_not_called()
    em.assert_not_called()


def test_oauth_links_existing_email_password_user_google(
    oauth_http_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = unique_email("go_link")
    password = "localPassword123"
    reg = register_user(oauth_http_client, email, password)
    uid = reg["user"]["id"]
    sub = f"google-sub-{uuid.uuid4().hex}"
    get_settings.cache_clear()
    state = create_google_oauth_state(get_settings())
    ex, ui = mock_google_provider(sub=sub, email=email)
    with (
        patch("app.services.google_oauth_service.exchange_authorization_code", ex),
        patch("app.services.google_oauth_service.fetch_userinfo", ui),
    ):
        r = google_callback(oauth_http_client, state=state)
    data = exchange_oauth_code(oauth_http_client, r)
    assert data["user"]["id"] == uid
    assert asyncio.run(_count_users_by_email(email, live_db_url, monkeypatch)) == 1
