"""
GitHub OAuth HTTP flow with mocked token + GitHub API calls (real PostgreSQL).

Run: ``pytest tests/test_github_oauth_api_integration.py -m integration -v``
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
from app.integrations.oauth_state import create_github_oauth_state
from app.main import app
from app.models.enums import OAuthProvider
from app.models.user import OAuthAccount, User
from app.services.auth_exceptions import GithubOAuthProviderError
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
def _alembic_for_github_oauth() -> None:
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
def github_oauth_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-github-client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test-github-client-secret")
    monkeypatch.setenv(
        "GITHUB_OAUTH_REDIRECT_URI",
        "http://127.0.0.1:8000/api/v1/auth/github/callback",
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


def _mock_github_success(
    *,
    github_id: int,
    email: str,
    login: str = "gh-tester",
    name: str | None = "GitHub Tester",
    email_rows: list[dict] | None = None,
) -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    exchange = AsyncMock(return_value={"access_token": "mock-github-access-token"})
    user = AsyncMock(
        return_value={
            "id": github_id,
            "login": login,
            "name": name,
            "email": None,
        }
    )
    rows = email_rows if email_rows is not None else [
        {"email": email, "primary": True, "verified": True},
    ]
    emails = AsyncMock(return_value=rows)
    return exchange, user, emails


def _callback(
    client: TestClient,
    *,
    code: str | None = "github-auth-code",
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
    return client.get("/api/v1/auth/github/callback", params=params)


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


async def _count_oauth_github_by_sub(sub: str, live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        result = await session.execute(
            select(func.count()).select_from(OAuthAccount).where(
                OAuthAccount.provider == OAuthProvider.github,
                OAuthAccount.provider_user_id == sub,
            )
        )
        return int(result.scalar_one())


def _patch_github(exchange: AsyncMock, user: AsyncMock, emails: AsyncMock):
    return (
        patch("app.services.github_oauth_service.exchange_authorization_code", exchange),
        patch("app.services.github_oauth_service.fetch_user", user),
        patch("app.services.github_oauth_service.fetch_user_emails", emails),
    )


def test_github_callback_valid_payload_creates_user_and_exchange_returns_tokens(
    github_oauth_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = _unique_email("gh_new")
    gid = uuid.uuid4().int % 1_000_000_000
    sub = str(gid)
    get_settings.cache_clear()
    state = create_github_oauth_state(get_settings())
    ex, u, em = _mock_github_success(github_id=gid, email=email)

    with _patch_github(ex, u, em):
        r = _callback(github_oauth_client, state=state)

    data = _exchange_from_callback_response(github_oauth_client, r)
    assert data["user"]["email"] == email
    assert data["access_token"]
    assert data["refresh_token"]

    n_users = asyncio.run(_count_users_by_email(email, live_db_url, monkeypatch))
    n_links = asyncio.run(_count_oauth_github_by_sub(sub, live_db_url, monkeypatch))
    assert n_users == 1
    assert n_links == 1
    ex.assert_awaited_once()
    u.assert_awaited_once()
    em.assert_awaited_once()


def test_github_callback_missing_verified_email_safe_no_user(
    github_oauth_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No verified email from GitHub → redirect error, no user row."""
    email = _unique_email("gh_no_email")
    get_settings.cache_clear()
    state = create_github_oauth_state(get_settings())
    ex, u, em = _mock_github_success(
        github_id=uuid.uuid4().int % 1_000_000_000,
        email=email,
        email_rows=[],
    )

    with _patch_github(ex, u, em):
        r = _callback(github_oauth_client, state=state)

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["github_oauth_email_unavailable"]
    n_users = asyncio.run(_count_users_by_email(email, live_db_url, monkeypatch))
    assert n_users == 0
    u.assert_awaited_once()
    em.assert_awaited_once()


def test_github_callback_only_unverified_emails_rejected(
    github_oauth_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _unique_email("gh_unverified_probe")
    get_settings.cache_clear()
    state = create_github_oauth_state(get_settings())
    rows = [{"email": probe, "primary": True, "verified": False}]
    ex, u, em = _mock_github_success(
        github_id=999888777,
        email=probe,
        email_rows=rows,
    )

    with _patch_github(ex, u, em):
        r = _callback(github_oauth_client, state=state)

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["github_oauth_email_unavailable"]
    n_users = asyncio.run(_count_users_by_email(probe, live_db_url, monkeypatch))
    assert n_users == 0


def test_github_callback_existing_email_password_user_links(
    github_oauth_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = _unique_email("gh_link")
    password = "localPassword456"
    reg = _register(github_oauth_client, email, password)
    user_id_before = reg["user"]["id"]

    gid = uuid.uuid4().int % 1_000_000_000
    sub = str(gid)
    get_settings.cache_clear()
    state = create_github_oauth_state(get_settings())
    ex, u, em = _mock_github_success(github_id=gid, email=email)

    with _patch_github(ex, u, em):
        r = _callback(github_oauth_client, state=state)

    data = _exchange_from_callback_response(github_oauth_client, r)
    assert data["user"]["id"] == user_id_before
    assert data["user"]["email"] == email

    n_users = asyncio.run(_count_users_by_email(email, live_db_url, monkeypatch))
    n_links = asyncio.run(_count_oauth_github_by_sub(sub, live_db_url, monkeypatch))
    assert n_users == 1
    assert n_links == 1


def test_github_duplicate_provider_login_no_extra_rows(
    github_oauth_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = _unique_email("gh_dup")
    gid = uuid.uuid4().int % 1_000_000_000
    sub = str(gid)

    def run_flow() -> dict:
        get_settings.cache_clear()
        state = create_github_oauth_state(get_settings())
        ex, u, em = _mock_github_success(github_id=gid, email=email)
        with _patch_github(ex, u, em):
            r = _callback(github_oauth_client, state=state)
        return _exchange_from_callback_response(github_oauth_client, r)

    d1 = run_flow()
    d2 = run_flow()
    assert d1["user"]["id"] == d2["user"]["id"]
    assert asyncio.run(_count_users_by_email(email, live_db_url, monkeypatch)) == 1
    assert asyncio.run(_count_oauth_github_by_sub(sub, live_db_url, monkeypatch)) == 1


def test_github_callback_invalid_state_rejected(github_oauth_client: TestClient) -> None:
    ex, u, em = _mock_github_success(github_id=1, email="x@y.com")
    with _patch_github(ex, u, em):
        r = _callback(github_oauth_client, state="not-a-valid-jwt", code="any")

    loc, qs = _parse_redirect_location(r)
    assert "localhost:3000" in loc
    assert qs.get("oauth_error") == ["github_oauth_invalid_state"]
    assert "oauth_exchange_code" not in qs
    ex.assert_not_called()
    u.assert_not_called()
    em.assert_not_called()


def test_github_callback_malformed_missing_code(github_oauth_client: TestClient) -> None:
    get_settings.cache_clear()
    state = create_github_oauth_state(get_settings())
    ex, u, em = _mock_github_success(github_id=1, email="a@b.com")
    with _patch_github(ex, u, em):
        r = _callback(github_oauth_client, code="", state=state)

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["github_oauth_missing_code"]
    ex.assert_not_called()


def test_github_callback_malformed_missing_state(github_oauth_client: TestClient) -> None:
    ex, u, em = _mock_github_success(github_id=1, email="a@b.com")
    with _patch_github(ex, u, em):
        r = _callback(github_oauth_client, state=None, code="c")

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["github_oauth_invalid_state"]
    ex.assert_not_called()


def test_github_callback_provider_access_denied(github_oauth_client: TestClient) -> None:
    ex, u, em = _mock_github_success(github_id=1, email="a@b.com")
    with _patch_github(ex, u, em):
        r = _callback(github_oauth_client, error="access_denied", state=None, code=None)

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["github_oauth_denied"]
    ex.assert_not_called()


def test_github_callback_token_exchange_failure_redirects(
    github_oauth_client: TestClient,
) -> None:
    get_settings.cache_clear()
    state = create_github_oauth_state(get_settings())
    ex = AsyncMock(side_effect=GithubOAuthProviderError("fail"))
    u = AsyncMock()
    em = AsyncMock()

    with _patch_github(ex, u, em):
        r = _callback(github_oauth_client, state=state)

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["github_token_exchange_failed"]
    u.assert_not_called()
    em.assert_not_called()


def test_github_callback_userinfo_failure_redirects(github_oauth_client: TestClient) -> None:
    get_settings.cache_clear()
    state = create_github_oauth_state(get_settings())
    ex = AsyncMock(return_value={"access_token": "t"})
    u = AsyncMock(side_effect=GithubOAuthProviderError("user fail"))
    em = AsyncMock()

    with _patch_github(ex, u, em):
        r = _callback(github_oauth_client, state=state)

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["github_userinfo_failed"]
    em.assert_not_called()


def test_github_link_conflict_second_github_id_same_email(
    github_oauth_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = _unique_email("gh_conflict")
    gid_a = uuid.uuid4().int % 1_000_000_000
    gid_b = (uuid.uuid4().int % 1_000_000_000) or 1
    if gid_b == gid_a:
        gid_b = gid_a + 1
    sub_a = str(gid_a)
    sub_b = str(gid_b)

    def run(*, gid: int):
        get_settings.cache_clear()
        state = create_github_oauth_state(get_settings())
        ex, u, em = _mock_github_success(github_id=gid, email=email)
        with _patch_github(ex, u, em):
            return _callback(github_oauth_client, state=state)

    r_ok = run(gid=gid_a)
    _exchange_from_callback_response(github_oauth_client, r_ok)

    r_fail = run(gid=gid_b)
    _, qs = _parse_redirect_location(r_fail)
    assert qs.get("oauth_error") == ["github_oauth_link_conflict"]

    assert asyncio.run(_count_users_by_email(email, live_db_url, monkeypatch)) == 1
    assert asyncio.run(_count_oauth_github_by_sub(sub_a, live_db_url, monkeypatch)) == 1
    assert asyncio.run(_count_oauth_github_by_sub(sub_b, live_db_url, monkeypatch)) == 0


def test_github_exchange_code_single_use(github_oauth_client: TestClient) -> None:
    email = _unique_email("gh_once")
    gid = uuid.uuid4().int % 1_000_000_000
    get_settings.cache_clear()
    state = create_github_oauth_state(get_settings())
    ex, u, em = _mock_github_success(github_id=gid, email=email)

    with _patch_github(ex, u, em):
        r = _callback(github_oauth_client, state=state)

    _, qs = _parse_redirect_location(r)
    code = qs["oauth_exchange_code"][0]
    r1 = github_oauth_client.post("/api/v1/auth/oauth/exchange", json={"exchange_code": code})
    r2 = github_oauth_client.post("/api/v1/auth/oauth/exchange", json={"exchange_code": code})
    assert r1.status_code == 200
    assert r2.status_code == 401
    assert r2.json()["error"]["code"] == "oauth_exchange_invalid"


def test_github_token_response_without_access_token_redirects(
    github_oauth_client: TestClient,
) -> None:
    get_settings.cache_clear()
    state = create_github_oauth_state(get_settings())
    ex = AsyncMock(return_value={"scope": "read"})
    u = AsyncMock()
    em = AsyncMock()

    with _patch_github(ex, u, em):
        r = _callback(github_oauth_client, state=state)

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["github_token_exchange_failed"]
    u.assert_not_called()
    em.assert_not_called()


def test_github_user_missing_id_redirects(github_oauth_client: TestClient) -> None:
    email = _unique_email("gh_noid")
    get_settings.cache_clear()
    state = create_github_oauth_state(get_settings())
    ex = AsyncMock(return_value={"access_token": "t"})
    u = AsyncMock(return_value={"login": "ghost", "name": None, "email": None})
    em = AsyncMock(return_value=[{"email": email, "primary": True, "verified": True}])

    with _patch_github(ex, u, em):
        r = _callback(github_oauth_client, state=state)

    _, qs = _parse_redirect_location(r)
    assert qs.get("oauth_error") == ["github_oauth_provider_error"]
