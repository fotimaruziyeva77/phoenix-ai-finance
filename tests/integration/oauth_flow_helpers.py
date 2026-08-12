"""OAuth callback + exchange helpers (provider HTTP mocked; app + DB are real)."""

from __future__ import annotations

from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient


def parse_oauth_redirect(response) -> tuple[str, dict[str, list[str]]]:
    assert response.status_code == 302, response.text
    loc = response.headers["location"]
    parsed = urlparse(loc)
    return loc, parse_qs(parsed.query)


def exchange_oauth_code(client: TestClient, response) -> dict:
    _, qs = parse_oauth_redirect(response)
    codes = qs.get("oauth_exchange_code")
    assert codes, qs
    r = client.post("/api/v1/auth/oauth/exchange", json={"exchange_code": codes[0]})
    assert r.status_code == 200, r.text
    return r.json()


def mock_google_provider(*, sub: str, email: str, email_verified: bool = True, name: str | None = "OAuth User"):
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


def google_callback(
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


def mock_github_provider(
    *,
    github_id: int,
    email: str,
    login: str = "gh-tester",
    name: str | None = "GitHub Tester",
    email_rows: list[dict] | None = None,
):
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


def patch_github(exchange: AsyncMock, user: AsyncMock, emails: AsyncMock):
    from unittest.mock import patch

    return (
        patch("app.services.github_oauth_service.exchange_authorization_code", exchange),
        patch("app.services.github_oauth_service.fetch_user", user),
        patch("app.services.github_oauth_service.fetch_user_emails", emails),
    )


def github_callback(
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
