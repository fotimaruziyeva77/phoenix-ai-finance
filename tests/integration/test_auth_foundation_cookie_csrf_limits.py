"""
Cookie transport, CSRF on mutating auth routes, auth rate limits, optional Redis limiter.

* ``cookie_*`` — HttpOnly cookies + JSON body token omission.
* ``csrf_*`` — double-submit enforcement on ``POST /auth/refresh`` when cookies are present.
* ``rate_limit_*`` — sliding-window limits (in-memory by default; Redis when ``TEST_REDIS_URL`` is set).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration
from fastapi.testclient import TestClient

from app.core.config import get_settings

from tests.integration.auth_setup import assert_error_envelope, unique_email


def test_cookie_register_sets_session_cookies_and_omits_body_tokens(
    auth_cookie_client: TestClient,
) -> None:
    email = unique_email("cookie_reg")
    r = auth_cookie_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Cookie User"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["auth_transport"] == "cookie"
    assert data.get("access_token") is None
    assert data.get("refresh_token") is None
    assert data.get("csrf_token")
    jar = auth_cookie_client.cookies
    assert "bf_access" in jar
    assert "bf_refresh" in jar
    assert "bf_csrf" in jar


def test_cookie_me_uses_http_only_access_without_bearer_header(
    auth_cookie_client: TestClient,
) -> None:
    email = unique_email("cookie_me")
    reg = auth_cookie_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Me"},
    )
    assert reg.status_code == 201, reg.text
    r = auth_cookie_client.get("/api/v1/auth/me")
    assert r.status_code == 200, r.text
    assert r.json()["email"] == email


def test_cookie_bootstrap_reports_transport_and_csrf_hint(
    auth_cookie_client: TestClient,
) -> None:
    email = unique_email("boot")
    reg = auth_cookie_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Boot"},
    )
    assert reg.status_code == 201, reg.text
    r = auth_cookie_client.get("/api/v1/auth/bootstrap")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["authenticated"] is True
    assert body["auth_transport"] == "cookie"
    assert body.get("csrf_token")


def test_csrf_refresh_without_header_fails_with_403(
    auth_cookie_client: TestClient,
) -> None:
    email = unique_email("csrf")
    reg = auth_cookie_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Csrf"},
    )
    assert reg.status_code == 201, reg.text
    r = auth_cookie_client.post("/api/v1/auth/refresh", json={})
    assert_error_envelope(r, status_code=403, code="csrf_validation_failed")


def test_csrf_refresh_with_matching_header_succeeds(
    auth_cookie_client: TestClient,
) -> None:
    email = unique_email("csrf_ok")
    reg = auth_cookie_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Csrf Ok"},
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["csrf_token"]
    assert token
    r = auth_cookie_client.post(
        "/api/v1/auth/refresh",
        json={},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200, r.text
    assert r.json()["access_token"] is None
    assert "bf_access" in auth_cookie_client.cookies


def test_auth_login_rate_limit_returns_429_with_retry_after(
    auth_http_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RATE_LIMITING_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_LOGIN_PER_MINUTE", "3")
    get_settings.cache_clear()
    for _ in range(3):
        resp = auth_http_client.post(
            "/api/v1/auth/login",
            json={"email": "rate-limit-nouser@example.com", "password": "wrong"},
        )
        assert resp.status_code == 401, resp.text
    r4 = auth_http_client.post(
        "/api/v1/auth/login",
        json={"email": "rate-limit-nouser@example.com", "password": "wrong"},
    )
    assert r4.status_code == 429, r4.text
    assert "Retry-After" in r4.headers


def test_auth_login_rate_limit_with_redis_backend(
    auth_http_client_redis_limiter: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RATE_LIMITING_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_LOGIN_PER_MINUTE", "2")
    get_settings.cache_clear()
    for _ in range(2):
        resp = auth_http_client_redis_limiter.post(
            "/api/v1/auth/login",
            json={"email": "redis-rl@example.com", "password": "x"},
        )
        assert resp.status_code == 401, resp.text
    r3 = auth_http_client_redis_limiter.post(
        "/api/v1/auth/login",
        json={"email": "redis-rl@example.com", "password": "x"},
    )
    assert r3.status_code == 429, r3.text
