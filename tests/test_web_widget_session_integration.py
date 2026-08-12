"""
Web widget public session foundation (PostgreSQL + Alembic head).

Covers anonymous session create, continuity, bot linkage, channel = web_widget, CHECK constraint,
and privacy-oriented fields (no visitor User rows).
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
from app.lib.chat_channels import CONVERSATION_CHANNEL_ADMIN_TEST, CONVERSATION_CHANNEL_WEB_WIDGET
from app.models.ai_foundation import Conversation
from app.models.bot import Bot
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.bot_repository import BotRepository
from app.services.web_widget_session_exceptions import (
    WebWidgetSessionBotNotFoundError,
    WebWidgetSessionValidationError,
)
from app.services.web_widget_session_service import WebWidgetSessionService
from sqlalchemy import func, select, text
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
def _alembic_for_web_widget_session_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def _unique_email(prefix: str = "ww-session") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def test_anonymous_public_session_can_be_created_with_continuity_and_bot_linkage(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        owner_id: uuid.UUID | None = None
        bot_id: uuid.UUID | None = None
        visitor_key: str | None = None
        conv_id: uuid.UUID | None = None
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("owner"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                owner_id = owner.id
                bot = Bot(
                    owner_id=owner.id,
                    name="Session Test Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                bot_id = bot.id
                await session.commit()

            async with sm() as session:
                chat = AIChatRepository(session)
                bots = BotRepository(session)
                svc = WebWidgetSessionService(chat, bots)
                conv, visitor_key = await svc.get_or_create_conversation(
                    bot_id=bot_id,
                    visitor_session_key=None,
                    visitor_client_hint="  hint-one  ",
                )
                conv_id = conv.id
                assert conv.channel == CONVERSATION_CHANNEL_WEB_WIDGET
                assert conv.bot_id == bot_id
                assert conv.owner_id == owner_id
                assert conv.public_visitor_session_key == visitor_key
                assert conv.visitor_client_hint == "hint-one"
                assert conv.niche_id_snapshot == "education"
                assert len(visitor_key) >= 16
                await chat.commit()

            async with sm() as session:
                chat = AIChatRepository(session)
                bots = BotRepository(session)
                svc = WebWidgetSessionService(chat, bots)
                again, key2 = await svc.get_or_create_conversation(
                    bot_id=bot_id,
                    visitor_session_key=visitor_key,
                )
                assert again.id == conv_id
                assert key2 == visitor_key
                assert again.channel == CONVERSATION_CHANNEL_WEB_WIDGET

            async with sm() as session:
                owner_row = await session.get(User, owner_id)
                assert owner_row is not None
                web_for_bot = (
                    await session.execute(
                        select(func.count())
                        .select_from(Conversation)
                        .where(
                            Conversation.bot_id == bot_id,
                            Conversation.channel == CONVERSATION_CHANNEL_WEB_WIDGET,
                        )
                    )
                ).scalar_one()
                assert web_for_bot == 1
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_same_visitor_key_distinct_bots_are_distinct_conversations(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Partial unique is (bot_id, key); same key on another bot is a different row."""

    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        shared_key = "abcdefghijklmnop"
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("two-bots"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                b1 = Bot(
                    owner_id=owner.id,
                    name="B1",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                b2 = Bot(
                    owner_id=owner.id,
                    name="B2",
                    niche_id="retail",
                    goal_type="faq",
                    status="active",
                )
                session.add_all([b1, b2])
                await session.flush()
                bid1, bid2 = b1.id, b2.id
                await session.commit()

            async with sm() as session:
                chat = AIChatRepository(session)
                bots = BotRepository(session)
                svc = WebWidgetSessionService(chat, bots)
                c1, k1 = await svc.get_or_create_conversation(
                    bot_id=bid1,
                    visitor_session_key=shared_key,
                )
                c2, k2 = await svc.get_or_create_conversation(
                    bot_id=bid2,
                    visitor_session_key=shared_key,
                )
                assert k1 == k2 == shared_key
                assert c1.id != c2.id
                assert c1.bot_id == bid1
                assert c2.bot_id == bid2
                await chat.commit()
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_channel_separation_web_widget_vs_admin_test_dashboard(
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
                    email=_unique_email("chan"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Chan Bot",
                    niche_id="services",
                    goal_type="consulting",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                bid = bot.id
                oid = owner.id
                await session.commit()

            async with sm() as session:
                chat = AIChatRepository(session)
                bots = BotRepository(session)
                svc = WebWidgetSessionService(chat, bots)
                wconv, _ = await svc.get_or_create_conversation(
                    bot_id=bid,
                    visitor_session_key="zzzzzzzzzzzzzzzz",
                )
                dash = await chat.create_conversation(
                    bot_id=bid,
                    owner_id=oid,
                    channel=CONVERSATION_CHANNEL_ADMIN_TEST,
                    niche_id_snapshot="services",
                    visitor_client_hint=CONVERSATION_CHANNEL_ADMIN_TEST,
                )
                await chat.commit()
                wid, did = wconv.id, dash.id

            async with sm() as session:
                w = await session.get(Conversation, wid)
                d = await session.get(Conversation, did)
                assert w is not None and d is not None
                assert w.channel == CONVERSATION_CHANNEL_WEB_WIDGET
                assert w.public_visitor_session_key is not None
                assert d.channel == CONVERSATION_CHANNEL_ADMIN_TEST
                assert d.public_visitor_session_key == CONVERSATION_CHANNEL_ADMIN_TEST
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_web_widget_row_requires_public_visitor_session_key_at_database(
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
                    email=_unique_email("ck"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="CK Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                bad = Conversation(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    channel=CONVERSATION_CHANNEL_WEB_WIDGET,
                    status="active",
                    public_visitor_session_key=None,
                )
                session.add(bad)
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_unknown_bot_id_raises_not_found(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        try:
            sm = get_session_maker()
            async with sm() as session:
                chat = AIChatRepository(session)
                bots = BotRepository(session)
                svc = WebWidgetSessionService(chat, bots)
                with pytest.raises(WebWidgetSessionBotNotFoundError):
                    await svc.get_or_create_conversation(
                        bot_id=uuid.uuid4(),
                        visitor_session_key=None,
                    )
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_invalid_visitor_session_key_raises_validation_error(
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
                    email=_unique_email("val"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Val Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                bid = bot.id
                await session.commit()

            async with sm() as session:
                chat = AIChatRepository(session)
                bots = BotRepository(session)
                svc = WebWidgetSessionService(chat, bots)
                with pytest.raises(WebWidgetSessionValidationError):
                    await svc.get_or_create_conversation(
                        bot_id=bid,
                        visitor_session_key="short",
                    )
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_conversations_table_has_web_widget_session_columns(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        engine = create_async_engine(normalize_database_url(live_db_url), pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                cols = (
                    await conn.execute(
                        text(
                            """
                            SELECT column_name FROM information_schema.columns
                            WHERE table_schema = 'public' AND table_name = 'conversations'
                            AND column_name IN (
                                'public_visitor_session_key', 'visitor_client_hint'
                            )
                            """
                        )
                    )
                ).fetchall()
                names = {str(r[0]) for r in cols}
                assert names == {"public_visitor_session_key", "visitor_client_hint"}
        finally:
            await engine.dispose()

    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    asyncio.run(body())
