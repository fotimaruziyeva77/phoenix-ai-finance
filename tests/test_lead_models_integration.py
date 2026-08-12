"""
Lead model + ``leads`` table integration tests (PostgreSQL + Alembic head).

Covers migration presence, inserts, FK integrity, defaults, owner-scoping columns, and nullables.
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
from app.core.db import dispose_engine, get_session_maker, normalize_database_url
from app.models.ai_foundation import Conversation
from app.models.bot import Bot
from app.models.enums import UserRole
from app.models.lead import Lead
from app.models.user import User
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
def _alembic_for_lead_model_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def _unique_email(prefix: str = "lead-owner") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


# --- Migration ---


def test_leads_migration_applies_table_exists(live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Migrations through head create ``public.leads`` (clean apply)."""

    async def body() -> None:
        engine = create_async_engine(normalize_database_url(live_db_url), pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                row = (
                    await conn.execute(
                        text(
                            "SELECT 1 FROM information_schema.tables "
                            "WHERE table_schema = 'public' AND table_name = 'leads'"
                        )
                    )
                ).first()
                assert row is not None
        finally:
            await engine.dispose()

    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    asyncio.run(body())


# --- Model / FK / defaults ---


def test_lead_can_be_created_with_default_status_new(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("create"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Lead Capture Bot",
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
                )
                session.add(lead)
                await session.commit()
                lid = lead.id

            async with sm() as session:
                row = await session.get(Lead, lid)
                assert row is not None
                assert row.status == "new"
                assert row.bot_id == bot.id
                assert row.owner_id == owner.id
                assert row.conversation_id is None
                assert row.lead_score is None
                assert row.lead_temperature is None
                assert row.name is None
                assert row.phone is None
                assert row.summary is None
                assert row.source_channel is None
                assert row.collected_data_json is None
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_lead_foreign_key_rejects_invalid_bot_id(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("fk-bot"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()

                lead = Lead(
                    bot_id=uuid.uuid4(),
                    owner_id=owner.id,
                    niche_id="education",
                )
                session.add(lead)
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_lead_foreign_key_rejects_invalid_owner_id(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("fk-own-a"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="FK Owner Bot",
                    niche_id="education",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()

                lead = Lead(
                    bot_id=bot.id,
                    owner_id=uuid.uuid4(),
                    niche_id="education",
                )
                session.add(lead)
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_lead_accepts_valid_conversation_foreign_key(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("conv-fk"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Conv FK Bot",
                    niche_id="healthcare",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                conv = Conversation(bot_id=bot.id, owner_id=owner.id, status="active")
                session.add(conv)
                await session.flush()

                lead = Lead(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    conversation_id=conv.id,
                    niche_id="healthcare",
                )
                session.add(lead)
                await session.commit()
                lid = lead.id

            async with sm() as session:
                row = await session.get(Lead, lid)
                assert row is not None
                assert row.conversation_id == conv.id
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_lead_foreign_key_rejects_invalid_conversation_id(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("bad-conv"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Bad Conv Bot",
                    niche_id="education",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()

                lead = Lead(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    conversation_id=uuid.uuid4(),
                    niche_id="education",
                )
                session.add(lead)
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_lead_owner_scoping_columns_match_bot_owner(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``owner_id`` on lead is the same object as ``bot.owner_id`` when inserted consistently."""

    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("scope"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Scope Bot",
                    niche_id="dev_agency",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()

                lead = Lead(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    niche_id="dev_agency",
                    status="contacted",
                )
                session.add(lead)
                await session.commit()
                lid = lead.id

            async with sm() as session:
                row = await session.get(Lead, lid)
                b = await session.get(Bot, row.bot_id)
                assert row is not None and b is not None
                assert row.owner_id == b.owner_id
                assert row.owner_id == owner.id
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_lead_optional_fields_round_trip(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("opts"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Opts Bot",
                    niche_id="services",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()

                lead = Lead(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    niche_id="services",
                    lead_score=72,
                    lead_temperature="hot",
                    status="qualified",
                    name="Alex Rivera",
                    phone="+1-415-555-0100",
                    summary="Wants kitchen remodel quote",
                    source_channel="web_chat",
                    collected_data_json={"service_type": "plumbing", "urgency": "this week"},
                )
                session.add(lead)
                await session.commit()
                lid = lead.id

            async with sm() as session:
                row = await session.get(Lead, lid)
                assert row is not None
                assert row.lead_score == 72
                assert row.lead_temperature == "hot"
                assert row.status == "qualified"
                assert row.name == "Alex Rivera"
                assert row.phone == "+1-415-555-0100"
                assert row.summary == "Wants kitchen remodel quote"
                assert row.source_channel == "web_chat"
                assert row.collected_data_json == {
                    "service_type": "plumbing",
                    "urgency": "this week",
                }
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_lead_invalid_status_rejected_by_database(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("bad-status"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Bad Status Bot",
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
                    status="not_a_pipeline_stage",
                )
                session.add(lead)
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())
