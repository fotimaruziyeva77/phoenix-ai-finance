"""
Bot lifecycle audit integration tests.
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
from app.core.db import dispose_engine, normalize_database_url
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

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
def _alembic_for_bot_audit() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def bot_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "bot-audit") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register_and_get_access(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Bot Audit"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def _fetch_audit_events(live_db_url: str, entity_id: str) -> list[dict]:
    engine = create_async_engine(normalize_database_url(live_db_url), pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    """
                    SELECT action, actor_user_id, entity_type, entity_id, before_snapshot, after_snapshot
                    FROM audit_logs
                    WHERE entity_id = CAST(:entity_id AS uuid)
                    ORDER BY created_at ASC
                    """
                ),
                {"entity_id": entity_id},
            )
            rows = result.mappings().all()
            return [dict(row) for row in rows]
    finally:
        await engine.dispose()


def test_bot_lifecycle_writes_audit_events(bot_client: TestClient, live_db_url: str) -> None:
    access = _register_and_get_access(bot_client, _unique_email("owner"))

    create_resp = bot_client.post(
        "/api/v1/bots",
        headers=_auth_headers(access),
        json={
            "name": "Audited Bot",
            "niche_id": "education",
            "goal_type": "support",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    bot_id = str(created["id"])
    owner_id = str(created["owner_id"])

    update_resp = bot_client.patch(
        f"/api/v1/bots/{bot_id}",
        headers=_auth_headers(access),
        json={"name": "Audited Bot Updated", "status": "active"},
    )
    assert update_resp.status_code == 200, update_resp.text

    archive_resp = bot_client.post(
        f"/api/v1/bots/{bot_id}/archive",
        headers=_auth_headers(access),
    )
    assert archive_resp.status_code == 200, archive_resp.text

    events = asyncio.run(_fetch_audit_events(live_db_url, bot_id))
    assert len(events) >= 3
    actions = [str(event["action"]) for event in events]
    assert "bot_created" in actions
    assert "bot_updated" in actions
    assert "bot_archived" in actions

    for event in events:
        assert str(event["actor_user_id"]) == owner_id
        assert event["entity_type"] == "bot"
        assert str(event["entity_id"]) == bot_id

    created_event = next(event for event in events if event["action"] == "bot_created")
    assert created_event["before_snapshot"] is None
    assert created_event["after_snapshot"] is not None
    assert created_event["after_snapshot"].get("name") == "Audited Bot"

    updated_event = next(event for event in events if event["action"] == "bot_updated")
    assert updated_event["before_snapshot"] is not None
    assert updated_event["after_snapshot"] is not None
    assert updated_event["before_snapshot"].get("name") == "Audited Bot"
    assert updated_event["after_snapshot"].get("name") == "Audited Bot Updated"

    archived_event = next(event for event in events if event["action"] == "bot_archived")
    assert archived_event["before_snapshot"] is not None
    assert archived_event["after_snapshot"] is not None
    assert archived_event["before_snapshot"].get("status") in {
        "draft",
        "active",
        "paused",
        "archived",
        "channel_pending",
    }
    assert archived_event["after_snapshot"].get("status") == "archived"
