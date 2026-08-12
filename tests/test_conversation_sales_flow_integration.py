"""
Integration: conversation sales-flow columns (migration + ORM persistence).

Requires PostgreSQL and ``TEST_DATABASE_URL`` / host-reachable ``DATABASE_URL``.
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
from app.models.ai_foundation import Conversation
from app.models.bot import Bot
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.ai_chat_repository import AIChatRepository
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
def _alembic_for_conversation_sales_flow_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def _unique_email(prefix: str = "conv-flow") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def test_conversation_defaults_for_minimal_orm_insert(live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """New row: current_state=start, collected_data_json={}, intent null, timestamps null."""

    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("def-owner"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()

                bot = Bot(
                    owner_id=owner.id,
                    name="Flow Default Bot",
                    niche_id="test_niche",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()

                conv = Conversation(bot_id=bot.id, owner_id=owner.id, status="active")
                session.add(conv)
                await session.commit()

                cid = conv.id
            async with sm() as session:
                row = await session.get(Conversation, cid)
                assert row is not None
                assert row.current_state == ConversationFlowState.start.value
                assert row.detected_intent is None
                assert row.niche_id_snapshot is None
                assert row.collected_data_json == {}
                assert row.last_user_message_at is None
                assert row.last_assistant_message_at is None
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_conversation_persists_state_intent_and_collected_json(
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
                    email=_unique_email("persist-owner"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Flow Persist Bot",
                    niche_id="ecommerce",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                conv = Conversation(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    status="active",
                    current_state=ConversationFlowState.qualification.value,
                    detected_intent=ConversationDetectedIntent.sales_interest.value,
                    niche_id_snapshot="ecommerce",
                    collected_data_json={"budget": "5k", "timeline": "Q2"},
                )
                session.add(conv)
                await session.commit()
                cid = conv.id

            async with sm() as session:
                row = await session.get(Conversation, cid)
                assert row is not None
                assert row.current_state == "qualification"
                assert row.detected_intent == "sales_interest"
                assert row.niche_id_snapshot == "ecommerce"
                assert row.collected_data_json == {"budget": "5k", "timeline": "Q2"}
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_conversation_invalid_current_state_rejected_by_database(
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
                    email=_unique_email("bad-state"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Bad State Bot",
                    niche_id="x",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                session.add(
                    Conversation(
                        bot_id=bot.id,
                        owner_id=owner.id,
                        status="active",
                        current_state="not_a_real_state",
                    ),
                )
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_conversation_invalid_detected_intent_rejected_by_database(
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
                    email=_unique_email("bad-intent"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Bad Intent Bot",
                    niche_id="x",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                session.add(
                    Conversation(
                        bot_id=bot.id,
                        owner_id=owner.id,
                        status="active",
                        detected_intent="purchase_order",  # not in allowed set
                    ),
                )
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_repository_stamps_last_message_timestamps(live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """AIChatRepository.add_message updates last_user_message_at / last_assistant_message_at."""

    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("stamp-owner"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Stamp Bot",
                    niche_id="svc",
                    goal_type="support",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                conv = Conversation(bot_id=bot.id, owner_id=owner.id, status="active")
                session.add(conv)
                await session.flush()
                cid, bid = conv.id, bot.id
                repo = AIChatRepository(session)
                umsg = await repo.add_message(
                    conversation_id=cid,
                    bot_id=bid,
                    role="user",
                    content="hi",
                )
                amsg = await repo.add_message(
                    conversation_id=cid,
                    bot_id=bid,
                    role="assistant",
                    content="hello",
                )
                await session.commit()
                uid_ts = umsg.created_at
                aid_ts = amsg.created_at

            async with sm() as session:
                row = await session.get(Conversation, cid)
                assert row is not None
                assert row.last_user_message_at == uid_ts
                assert row.last_assistant_message_at == aid_ts
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_collected_data_json_round_trips_nested_structure(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload: dict = {"lead": {"email": "a@b.co", "tags": ["warm", "b2b"]}, "step": 2}

    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("json-owner"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="JSON Bot",
                    niche_id="x",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                conv = Conversation(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    status="active",
                    collected_data_json=payload,
                )
                session.add(conv)
                await session.commit()
                cid = conv.id

            async with sm() as session:
                row = await session.get(Conversation, cid)
                assert row is not None
                assert row.collected_data_json == payload
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())
