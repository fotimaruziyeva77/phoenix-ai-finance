"""
Sprint 5 bot creation flow integration checks.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.db import dispose_engine
from app.main import app
from fastapi.testclient import TestClient

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
            "Set TEST_DATABASE_URL (recommended) or host-reachable DATABASE_URL "
            "(not @postgres: — use 127.0.0.1 when testing from the host)."
        ),
    ),
]


def _alembic_upgrade_head(url: str) -> None:
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
def _alembic_for_sprint5_flow() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def bot_flow_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "sprint5-flow") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register_and_get_access(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Sprint 5 Flow"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_sprint5_bot_create_flow_end_to_end(bot_flow_client: TestClient) -> None:
    access = _register_and_get_access(bot_flow_client, _unique_email())

    create = bot_flow_client.post(
        "/api/v1/bots",
        headers=_auth_headers(access),
        json={
            "name": "Sprint5 Bot",
            "niche_id": "education",
            "goal_type": "support",
            "short_description": "Created from sprint5 integration flow",
        },
    )
    assert create.status_code == 201, create.text
    created = create.json()
    bot_id = created["id"]
    assert created["name"] == "Sprint5 Bot"
    assert created["status"] == "draft"

    listed = bot_flow_client.get("/api/v1/bots", headers=_auth_headers(access))
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    assert any(item["id"] == bot_id and item["name"] == "Sprint5 Bot" for item in items)

    fetched = bot_flow_client.get(f"/api/v1/bots/{bot_id}", headers=_auth_headers(access))
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["id"] == bot_id

    invalid = bot_flow_client.post(
        "/api/v1/bots",
        headers=_auth_headers(access),
        json={
            "name": "Invalid Bot",
            "niche_id": "not_supported",
            "goal_type": "support",
        },
    )
    assert invalid.status_code == 422, invalid.text
    body = invalid.json()
    assert body.get("error", {}).get("code") in {"bot_validation_error", "validation_error"}
