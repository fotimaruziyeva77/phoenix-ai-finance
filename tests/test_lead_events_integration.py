"""
Lead CRM timeline (``lead_events``) — PostgreSQL + API integration.

Covers append-only rows, lifecycle emissions, timeline ordering, and DB enforcement.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.main import app
from app.models.bot import Bot
from app.models.lead import Lead
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.lead_event_repository import LeadEventRepository
from app.services.lead_event_service import LeadEventService
from sqlalchemy import select, text

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
def _alembic_for_lead_events() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
async def events_client(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
) -> AsyncIterator[httpx.AsyncClient]:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    await dispose_engine()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await dispose_engine()
    get_settings.cache_clear()


def _unique_email(prefix: str = "lead-ev") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


async def _register_and_get_access(client: httpx.AsyncClient, email: str) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Lead Events"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def _user_id_for_email(email: str) -> uuid.UUID:
    sm = get_session_maker()
    async with sm() as session:
        row = (await session.execute(select(User).where(User.email == email).limit(1))).scalar_one()
        return row.id


async def _create_lead_for_owner_email(owner_email: str) -> uuid.UUID:
    sm = get_session_maker()
    async with sm() as session:
        owner = (
            await session.execute(select(User).where(User.email == owner_email).limit(1))
        ).scalar_one()
        bot = Bot(
            owner_id=owner.id,
            name="Events Bot",
            niche_id="education",
            goal_type="sales",
            status="active",
        )
        session.add(bot)
        await session.flush()
        lead = Lead(
            bot_id=bot.id,
            owner_id=owner.id,
            niche_id="education",
            lead_temperature="warm",
        )
        session.add(lead)
        await session.flush()
        ev = LeadEventService(LeadEventRepository(session))
        await ev.emit_lead_created(
            lead_id=lead.id,
            bot_id=bot.id,
            conversation_id=None,
            source_channel="admin_test",
            creation_reason="created",
        )
        await session.commit()
        return lead.id


@pytest.mark.asyncio
async def test_lead_timeline_status_notes_assign_notification_ordering(
    events_client: httpx.AsyncClient,
    live_db_url: str,
) -> None:
    owner_mail = _unique_email("ev-owner")
    assignee_mail = _unique_email("ev-assignee")
    owner_access = await _register_and_get_access(events_client, owner_mail)
    await _register_and_get_access(events_client, assignee_mail)
    assignee_id = await _user_id_for_email(assignee_mail)

    lead_id = await _create_lead_for_owner_email(owner_mail)

    # Status + notes (single PATCH)
    p1 = await events_client.patch(
        f"/api/v1/leads/{lead_id}/status",
        headers=_auth_headers(owner_access),
        json={"status": "contacted", "notes": "First call done."},
    )
    assert p1.status_code == 200, p1.text

    # Assignee then reassign to same user (no event) then to clear and set again for reassigned
    p2 = await events_client.patch(
        f"/api/v1/leads/{lead_id}/status",
        headers=_auth_headers(owner_access),
        json={"status": "contacted", "assignee_user_id": str(assignee_id)},
    )
    assert p2.status_code == 200, p2.text

    p3 = await events_client.patch(
        f"/api/v1/leads/{lead_id}/status",
        headers=_auth_headers(owner_access),
        json={"status": "contacted", "assignee_user_id": None},
    )
    assert p3.status_code == 200, p3.text

    p4 = await events_client.patch(
        f"/api/v1/leads/{lead_id}/status",
        headers=_auth_headers(owner_access),
        json={"status": "contacted", "assignee_user_id": str(assignee_id)},
    )
    assert p4.status_code == 200, p4.text

    sm = get_session_maker()
    async with sm() as session:
        ev = LeadEventService(LeadEventRepository(session))
        await ev.emit_notification_outcome(
            lead_id=lead_id,
            channel="telegram",
            ok=True,
            metadata={"attempts": 1},
        )
        await ev.emit_notification_outcome(
            lead_id=lead_id,
            channel="telegram",
            ok=False,
            metadata={"attempts": 3, "error_kind": "http_error"},
        )
        await session.commit()

    # GET detail records lead_viewed
    g = await events_client.get(
        f"/api/v1/leads/{lead_id}",
        headers=_auth_headers(owner_access),
    )
    assert g.status_code == 200, g.text

    timeline = await events_client.get(
        f"/api/v1/leads/{lead_id}/events",
        headers=_auth_headers(owner_access),
    )
    assert timeline.status_code == 200, timeline.text
    body = timeline.json()
    assert body["total"] >= 8
    types = [e["event_type"] for e in body["items"]]
    assert types[0] == "lead_created"
    assert "lead_status_changed" in types
    assert "note_added" in types
    assert types.count("lead_assigned") >= 1
    assert "lead_reassigned" in types
    assert "notification_delivered" in types
    assert "notification_failed" in types
    assert types[-1] == "lead_viewed"

    # Chronological order: created_at non-decreasing
    prev_t = None
    for e in body["items"]:
        t = e["created_at"]
        if prev_t is not None:
            assert t >= prev_t
        prev_t = t


@pytest.mark.asyncio
async def test_lead_events_append_only_trigger(live_db_url: str) -> None:
    sm = get_session_maker()
    async with sm() as session:
        owner = User(
            email=_unique_email("append-only"),
            password_hash="bcrypt$dummy",
            role=UserRole.customer_admin,
        )
        session.add(owner)
        await session.flush()
        bot = Bot(
            owner_id=owner.id,
            name="B",
            niche_id="generic",
            goal_type="sales",
            status="active",
        )
        session.add(bot)
        await session.flush()
        lead = Lead(bot_id=bot.id, owner_id=owner.id, niche_id="generic")
        session.add(lead)
        await session.flush()
        repo = LeadEventRepository(session)
        row = await repo.insert_event(
            lead_id=lead.id,
            event_type="system_action",
            actor_type="system",
            actor_id=None,
            old_value=None,
            new_value="probe",
            metadata={"probe": True},
        )
        await session.commit()
        eid = row.id

    sm2 = get_session_maker()
    async with sm2() as session:
        with pytest.raises(Exception, match="append-only|lead_events"):
            await session.execute(text("UPDATE lead_events SET new_value = 'nope' WHERE id = :id"), {"id": eid})
            await session.commit()


@pytest.mark.asyncio
async def test_invalid_assignee_patch_returns_clean_validation_error(
    events_client: httpx.AsyncClient,
) -> None:
    owner_mail = _unique_email("bad-assignee")
    owner_access = await _register_and_get_access(events_client, owner_mail)
    lead_id = await _create_lead_for_owner_email(owner_mail)
    bad = uuid.uuid4()
    r = await events_client.patch(
        f"/api/v1/leads/{lead_id}/status",
        headers=_auth_headers(owner_access),
        json={"status": "new", "assignee_user_id": str(bad)},
    )
    assert r.status_code == 422, r.text
    payload = r.json()
    assert payload.get("error", {}).get("code") == "lead_pipeline_validation_error"
