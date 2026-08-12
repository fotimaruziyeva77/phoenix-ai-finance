"""
Bot model integration tests (PostgreSQL + applied migrations).
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
from app.core.db import dispose_engine, get_session_maker
from app.models.bot import Bot
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.bots import BotCreate, BotListItem, BotRead, BotUpdate
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

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
def _alembic_for_bot_model_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def _run_async_db(live_db_url: str, monkeypatch: pytest.MonkeyPatch, coro) -> None:
    async def runner() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        try:
            await coro
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(runner())


def _unique_email(prefix: str = "bot-owner") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def test_bot_row_create_and_owner_relationship_works(live_db_url, monkeypatch):
    owner_email = _unique_email("owner")

    async def body() -> None:
        sm = get_session_maker()
        async with sm() as session:
            owner = User(
                email=owner_email,
                password_hash="bcrypt$dummy",
                role=UserRole.customer_admin,
            )
            session.add(owner)
            await session.flush()

            bot = Bot(
                owner_id=owner.id,
                name="Lead Assistant",
                niche_id="services_local",
                goal_type="sales",
                status="draft",
                welcome_message="Hi, how can I help?",
                tone="friendly",
                language="en",
                short_description="Collects warm leads from website visitors.",
            )
            session.add(bot)
            await session.commit()
            await session.refresh(bot)

            assert bot.id is not None
            assert bot.owner_id == owner.id
            assert bot.goal_type == "sales"
            assert bot.status == "draft"

        async with sm() as session:
            row = await session.scalar(select(Bot).where(Bot.name == "Lead Assistant"))
            assert row is not None
            await session.refresh(row, attribute_names=["owner"])
            assert row.owner is not None
            assert row.owner.email == owner_email

            owner = await session.scalar(select(User).where(User.email == owner_email))
            assert owner is not None
            await session.refresh(owner, attribute_names=["bots"])
            assert len(owner.bots) == 1
            assert owner.bots[0].id == row.id

            await session.delete(row)
            await session.delete(owner)
            await session.commit()

    _run_async_db(live_db_url, monkeypatch, body())


def test_invalid_bot_status_rejected_by_database_constraint(live_db_url, monkeypatch):
    owner_email = _unique_email("invalid-status-owner")

    async def body() -> None:
        sm = get_session_maker()
        async with sm() as session:
            owner = User(
                email=owner_email,
                password_hash="bcrypt$dummy",
                role=UserRole.customer_admin,
            )
            session.add(owner)
            await session.flush()

            session.add(
                Bot(
                    owner_id=owner.id,
                    name="Broken Status Bot",
                    niche_id="education",
                    goal_type="support",
                    status="unknown",
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

        async with sm() as session:
            owner = await session.scalar(select(User).where(User.email == owner_email))
            if owner is not None:
                await session.delete(owner)
                await session.commit()

    _run_async_db(live_db_url, monkeypatch, body())


def test_bot_schema_shape_and_constraints() -> None:
    create = BotCreate(
        name="Support Bot",
        niche_id="faq_global",
        goal_type="faq",
        status="active",
    )
    patch = BotUpdate(status="paused", tone="professional")
    read = BotRead(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        name="Support Bot",
        niche_id="faq_global",
        goal_type="faq",
        status="active",
        primary_channel=None,
        welcome_message=None,
        tone=None,
        language="en",
        short_description=None,
        provider_name="gemini",
        model_name=None,
        temperature=None,
        max_output_tokens=None,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
    )
    item = BotListItem(
        id=uuid.uuid4(),
        name="Support Bot",
        niche_id="faq_global",
        goal_type="faq",
        status="active",
        updated_at="2026-01-02T00:00:00Z",
    )

    assert create.goal_type == "faq"
    assert patch.status == "paused"
    assert read.language == "en"
    assert item.niche_id == "faq_global"

    with pytest.raises(ValidationError):
        BotCreate(name="X", niche_id="n1", goal_type="invalid")
