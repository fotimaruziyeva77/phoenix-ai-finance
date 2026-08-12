"""Reusable TestClient factories (bearer vs cookie auth, optional Redis-backed limiter)."""

from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.db import dispose_engine
from app.main import app

from tests.integration.auth_setup import apply_auth_test_env


@pytest.fixture
def auth_http_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    apply_auth_test_env(monkeypatch, live_db_url)
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


@pytest.fixture
def auth_cookie_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    apply_auth_test_env(
        monkeypatch,
        live_db_url,
        extra={
            "AUTH_COOKIE_ENABLED": "true",
            "AUTH_COOKIE_SECURE": "false",
            "AUTH_COOKIE_OMIT_BODY_TOKENS": "true",
        },
    )
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


@pytest.fixture
def auth_http_client_redis_limiter(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    """
    Same as ``auth_http_client`` but points the app at ``TEST_REDIS_URL`` when set.

    Skips if unset so local runs without Redis stay green; CI can set ``TEST_REDIS_URL``.
    """
    redis_url = os.environ.get("TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("Set TEST_REDIS_URL to exercise Redis-backed auth rate limits.")
    extra = {"REDIS_URL": redis_url, "RATE_LIMIT_REDIS_URL": redis_url}
    apply_auth_test_env(monkeypatch, live_db_url, extra=extra)
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()
