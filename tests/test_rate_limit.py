"""In-memory rate limiter + auth endpoint wiring (isolated limiter state)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from app.api import deps as api_deps
from app.core.config import get_settings
from app.core.limiters.memory_sliding_window import InMemorySlidingWindowLimiter
from app.main import app
from app.services.auth_exceptions import InvalidCredentialsError
from fastapi.testclient import TestClient


def _mock_auth_service_invalid_login() -> None:
    """Override without sub-dependency parameters (avoids FastAPI treating them as query params)."""

    def override_auth_service() -> AsyncMock:
        svc = AsyncMock()
        svc.login = AsyncMock(side_effect=InvalidCredentialsError())
        return svc

    app.dependency_overrides[api_deps.get_auth_service] = override_auth_service


def test_invalid_credentials_error_has_authentication_category() -> None:
    _mock_auth_service_invalid_login()
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            r = client.post(
                "/api/v1/auth/login",
                json={"email": "ghost@example.com", "password": "doesnotmatter1"},
            )
        assert r.status_code == 401
        err = r.json()["error"]
        assert err["code"] == "invalid_credentials"
        assert err["category"] == "authentication"
    finally:
        app.dependency_overrides.pop(api_deps.get_sliding_window_limiter, None)
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_sliding_window_blocks_after_limit() -> None:
    lim = InMemorySlidingWindowLimiter()

    async def run() -> None:
        assert await lim.allow("k", limit=2, window_seconds=60.0)
        assert await lim.allow("k", limit=2, window_seconds=60.0)
        assert not await lim.allow("k", limit=2, window_seconds=60.0)

    asyncio.run(run())


def test_login_returns_429_when_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    lim = InMemorySlidingWindowLimiter()
    app.dependency_overrides[api_deps.get_sliding_window_limiter] = lambda: lim
    monkeypatch.setenv("APP_RATE_LIMIT_LOGIN_PER_MINUTE", "1")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    _mock_auth_service_invalid_login()
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            r1 = client.post(
                "/api/v1/auth/login",
                json={"email": "nope@example.com", "password": "secret123"},
            )
            r2 = client.post(
                "/api/v1/auth/login",
                json={"email": "nope@example.com", "password": "secret123"},
            )
        assert r1.status_code == 401
        assert r2.status_code == 429
        body = r2.json()
        assert body["error"]["code"] == "rate_limit_exceeded"
        assert body["error"]["category"] == "authentication"
    finally:
        app.dependency_overrides.pop(api_deps.get_sliding_window_limiter, None)
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_refresh_returns_429_when_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    lim = InMemorySlidingWindowLimiter()
    app.dependency_overrides[api_deps.get_sliding_window_limiter] = lambda: lim
    monkeypatch.setenv("APP_RATE_LIMIT_REFRESH_PER_MINUTE", "1")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            r1 = client.post("/api/v1/auth/refresh", json={})
            r2 = client.post("/api/v1/auth/refresh", json={})
        assert r1.status_code == 422
        assert r2.status_code == 429
        assert r2.json()["error"]["code"] == "rate_limit_exceeded"
    finally:
        app.dependency_overrides.pop(api_deps.get_sliding_window_limiter, None)
        app.dependency_overrides.clear()
        get_settings.cache_clear()
