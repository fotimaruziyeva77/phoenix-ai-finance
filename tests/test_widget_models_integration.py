"""
WidgetConfig ORM integration tests (PostgreSQL + Alembic head).

Covers inserts, ``public_widget_key`` uniqueness, JSON persistence, FK integrity, and relations.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker, normalize_database_url
from app.models.bot import Bot
from app.models.enums import UserRole
from app.models.user import User
from app.models.widget_config import WidgetConfig, new_public_widget_key
from sqlalchemy import select, text
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
def _alembic_for_widget_model_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def _unique_email(prefix: str = "widget-owner") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def test_widget_configs_table_exists_after_migrations(live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    async def body() -> None:
        engine = create_async_engine(normalize_database_url(live_db_url), pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                row = (
                    await conn.execute(
                        text(
                            "SELECT 1 FROM information_schema.tables "
                            "WHERE table_schema = 'public' AND table_name = 'widget_configs'"
                        )
                    )
                ).first()
                assert row is not None
        finally:
            await engine.dispose()

    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    asyncio.run(body())


def test_widget_config_can_be_created(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        key = new_public_widget_key()
        domains = ["app.example.com", "partner.org"]
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
                    name="Widget Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                session.add(bot)
                await session.flush()

                wc = WidgetConfig(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    public_widget_key=key,
                    allowed_domains_json=domains,
                    theme="dark",
                    welcome_text="Hello from the widget",
                )
                session.add(wc)
                await session.commit()
                wid = wc.id

            async with sm() as session:
                row = await session.get(WidgetConfig, wid)
                assert row is not None
                assert row.public_widget_key == key
                assert row.bot_id == bot.id
                assert row.owner_id == owner.id
                assert row.is_enabled is True
                assert row.allowed_domains_json == domains
                assert row.theme == "dark"
                assert row.welcome_text == "Hello from the widget"
                assert row.widget_settings_json is None
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_public_widget_key_uniqueness_enforced(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        shared_key = "test-shared-key-" + uuid.uuid4().hex
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("uq-a"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot_a = Bot(
                    owner_id=owner.id,
                    name="Bot A",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                session.add(bot_a)
                await session.flush()

                session.add(
                    WidgetConfig(
                        bot_id=bot_a.id,
                        owner_id=owner.id,
                        public_widget_key=shared_key,
                    )
                )
                await session.commit()

            async with sm() as session:
                owner2 = User(
                    email=_unique_email("uq-b"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner2)
                await session.flush()
                bot_b2 = Bot(
                    owner_id=owner2.id,
                    name="Other Bot",
                    niche_id="healthcare",
                    goal_type="faq",
                    status="active",
                )
                session.add(bot_b2)
                await session.flush()
                session.add(
                    WidgetConfig(
                        bot_id=bot_b2.id,
                        owner_id=owner2.id,
                        public_widget_key=shared_key,
                    )
                )
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_allowed_domains_json_round_trips_via_raw_sql(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JSONB list survives ORM round-trip and is visible as JSON from SQL."""

    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        key = new_public_widget_key()
        domains = ["cdn.example.com", "shop.example.co.uk"]
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("json"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="JSON Bot",
                    niche_id="retail",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                wc = WidgetConfig(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    public_widget_key=key,
                    allowed_domains_json=domains,
                )
                session.add(wc)
                await session.commit()
                wid = wc.id

            async with sm() as session:
                raw = (
                    await session.execute(
                        text("SELECT allowed_domains_json::text FROM widget_configs WHERE id = :id"),
                        {"id": wid},
                    )
                ).scalar_one()
                assert raw is not None
                assert json.loads(raw) == domains

                row = await session.get(WidgetConfig, wid)
                assert row is not None
                assert row.allowed_domains_json == domains
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_widget_config_foreign_key_rejects_invalid_bot_id(
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
                session.add(
                    WidgetConfig(
                        bot_id=uuid.uuid4(),
                        owner_id=owner.id,
                        public_widget_key=new_public_widget_key(),
                    )
                )
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_widget_config_foreign_key_rejects_invalid_owner_id(
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
                    email=_unique_email("fk-own"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="FK Owner Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                session.add(
                    WidgetConfig(
                        bot_id=bot.id,
                        owner_id=uuid.uuid4(),
                        public_widget_key=new_public_widget_key(),
                    )
                )
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_widget_config_bot_and_owner_relationships_resolve(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        key = new_public_widget_key()
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("rel"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Rel Bot",
                    niche_id="consulting",
                    goal_type="consulting",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                wc = WidgetConfig(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    public_widget_key=key,
                )
                session.add(wc)
                await session.commit()
                wid = wc.id

            async with sm() as session:
                row = await session.get(WidgetConfig, wid)
                assert row is not None
                await session.refresh(row, attribute_names=["bot", "owner"])
                assert row.bot is not None
                assert row.owner is not None
                assert row.bot.id == row.bot_id
                assert row.owner.id == row.owner_id
                assert row.bot.owner_id == row.owner_id

                bots_widgets = (
                    await session.execute(select(WidgetConfig).where(WidgetConfig.bot_id == bot.id))
                ).scalars().all()
                assert len(bots_widgets) >= 1
                assert any(w.id == wid for w in bots_widgets)
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_widget_config_cascades_when_bot_deleted(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        key = new_public_widget_key()
        try:
            sm = get_session_maker()
            bot_id: uuid.UUID | None = None
            wid: uuid.UUID | None = None
            async with sm() as session:
                owner = User(
                    email=_unique_email("cascade"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Cascade Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                bot_id = bot.id
                wc = WidgetConfig(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    public_widget_key=key,
                )
                session.add(wc)
                await session.commit()
                wid = wc.id

            async with sm() as session:
                bot_row = await session.get(Bot, bot_id)
                assert bot_row is not None
                await session.delete(bot_row)
                await session.commit()

            async with sm() as session:
                assert await session.get(WidgetConfig, wid) is None
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())
