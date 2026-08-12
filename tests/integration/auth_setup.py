"""Shared DB migration, JWT test secret, and HTTP helpers for auth integration tests."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.db import dispose_engine
from app.core.security import decode_token

PROJECT_ROOT = Path(__file__).resolve().parents[2]

JWT_INTEGRATION_KEY = "x" * 32


def alembic_upgrade_head(database_url: str) -> None:
    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
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


def unique_email(prefix: str = "auth") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def assert_error_envelope(
    response,
    *,
    status_code: int,
    code: str | None = None,
    category: str | None = None,
) -> dict:
    assert response.status_code == status_code, response.text
    data = response.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    if code is not None:
        assert data["error"]["code"] == code
    if category is not None:
        assert data["error"].get("category") == category
    return data


def register_user(client: TestClient, email: str, password: str = "password123") -> dict:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Integration Test"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def login_user(client: TestClient, email: str, password: str) -> dict:
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200, r.text
    return r.json()


def refresh_jti(refresh_token: str, settings: Settings) -> str:
    payload = decode_token(
        refresh_token,
        settings=settings,
        expected_token_type="refresh",
    )
    jti = payload.get("jti")
    assert isinstance(jti, str) and jti.strip()
    return jti.strip()


def apply_auth_test_env(
    monkeypatch,
    live_db_url: str,
    *,
    extra: dict[str, str] | None = None,
) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    if extra:
        for k, v in extra.items():
            monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    # New pool for this DATABASE_URL
    import asyncio

    asyncio.run(dispose_engine())
