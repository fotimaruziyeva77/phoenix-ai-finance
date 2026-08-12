"""
AI foundation ORM integration tests (PostgreSQL + applied migrations).
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.models.ai_foundation import (
    AIUsageLog,
    Conversation,
    DailyAIUsageAggregate,
    Message,
)
from app.models.bot import Bot
from app.models.enums import UserRole
from app.models.user import User
from app.services.ai_usage_aggregation_service import AIUsageAggregationService
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
def _alembic_for_ai_foundation_model_tests() -> None:
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


def _unique_email(prefix: str = "ai-owner") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def test_conversation_message_usage_log_and_aggregate_create_with_relationships(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("conv-msg")

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
                name="AI Test Bot",
                niche_id="services_local",
                goal_type="support",
                status="active",
            )
            session.add(bot)
            await session.flush()

            conv = Conversation(
                bot_id=bot.id,
                owner_id=owner.id,
                channel=None,
                status="active",
            )
            session.add(conv)
            await session.flush()

            msg = Message(
                conversation_id=conv.id,
                bot_id=bot.id,
                role="user",
                content="Hello",
                tokens_input=10,
                tokens_output=None,
                tokens_total=10,
                latency_ms=100,
                cost_usd=Decimal("0.00001234"),
                model_name="gpt-4o-mini",
            )
            session.add(msg)
            await session.flush()

            log = AIUsageLog(
                bot_id=bot.id,
                conversation_id=conv.id,
                message_id=msg.id,
                provider_name="openai",
                model_name="gpt-4o-mini",
                tokens_input=10,
                tokens_output=5,
                tokens_total=15,
                latency_ms=120,
                cost_usd=Decimal("0.00002"),
                success=True,
                error_code=None,
            )
            session.add(log)

            agg = DailyAIUsageAggregate(
                bot_id=bot.id,
                usage_date=date(2026, 4, 2),
                total_requests=3,
                total_tokens=1500,
                total_cost_usd=Decimal("0.05"),
                avg_latency_ms=Decimal("200.5000"),
            )
            session.add(agg)
            await session.commit()

            await session.refresh(conv)
            await session.refresh(bot)
            await session.refresh(msg)
            await session.refresh(log)
            await session.refresh(agg)

            assert conv.bot_id == bot.id
            assert conv.owner_id == owner.id
            assert msg.conversation_id == conv.id
            assert log.message_id == msg.id
            assert log.conversation_id == conv.id
            assert agg.bot_id == bot.id
            assert agg.total_cost_usd == Decimal("0.05")

        async with sm() as session:
            loaded_conv = await session.scalar(select(Conversation).where(Conversation.id == conv.id))
            assert loaded_conv is not None
            await session.refresh(loaded_conv, attribute_names=["bot", "messages", "owner"])
            assert loaded_conv.bot is not None
            assert loaded_conv.bot.id == bot.id
            assert loaded_conv.owner.email == owner_email
            assert len(loaded_conv.messages) == 1
            assert loaded_conv.messages[0].role == "user"

            loaded_bot = await session.scalar(select(Bot).where(Bot.id == bot.id))
            assert loaded_bot is not None
            await session.refresh(
                loaded_bot,
                attribute_names=["conversations", "messages", "ai_usage_logs", "daily_ai_usage_aggregates"],
            )
            assert len(loaded_bot.conversations) == 1
            assert len(loaded_bot.messages) == 1
            assert len(loaded_bot.ai_usage_logs) == 1
            assert len(loaded_bot.daily_ai_usage_aggregates) == 1

            owner_row = await session.scalar(select(User).where(User.email == owner_email))
            assert owner_row is not None
            await session.refresh(owner_row, attribute_names=["conversations"])
            assert len(owner_row.conversations) == 1

            await session.delete(owner_row)
            await session.commit()

    _run_async_db(live_db_url, monkeypatch, body())


def test_invalid_conversation_status_rejected_by_database(live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    owner_email = _unique_email("bad-conv-status")

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
                name="Bad Conv Bot",
                niche_id="education",
                goal_type="faq",
                status="active",
            )
            session.add(bot)
            await session.flush()
            session.add(
                Conversation(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    status="open",
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


def test_invalid_message_role_rejected_by_database(live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    owner_email = _unique_email("bad-msg-role")

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
                name="Bad Msg Bot",
                niche_id="education",
                goal_type="faq",
                status="active",
            )
            session.add(bot)
            await session.flush()
            conv = Conversation(bot_id=bot.id, owner_id=owner.id, status="active")
            session.add(conv)
            await session.flush()
            session.add(
                Message(
                    conversation_id=conv.id,
                    bot_id=bot.id,
                    role="tool",
                    content="{}",
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


def test_daily_aggregate_unique_per_bot_and_date(live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    owner_email = _unique_email("dup-agg")
    usage_day = date(2026, 4, 1)

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
                name="Agg Bot",
                niche_id="education",
                goal_type="faq",
                status="active",
            )
            session.add(bot)
            await session.flush()
            session.add(
                DailyAIUsageAggregate(
                    bot_id=bot.id,
                    usage_date=usage_day,
                    total_requests=1,
                    total_tokens=10,
                    total_cost_usd=Decimal("0"),
                )
            )
            await session.flush()
            session.add(
                DailyAIUsageAggregate(
                    bot_id=bot.id,
                    usage_date=usage_day,
                    total_requests=2,
                    total_tokens=20,
                    total_cost_usd=Decimal("0"),
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


def test_ai_usage_log_survives_message_delete_with_null_message_id(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("set-null-msg")

    async def body() -> None:
        sm = get_session_maker()
        log_id: uuid.UUID | None = None
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
                name="Set Null Bot",
                niche_id="education",
                goal_type="faq",
                status="active",
            )
            session.add(bot)
            await session.flush()
            conv = Conversation(bot_id=bot.id, owner_id=owner.id, status="active")
            session.add(conv)
            await session.flush()
            msg = Message(
                conversation_id=conv.id,
                bot_id=bot.id,
                role="assistant",
                content="Hi",
            )
            session.add(msg)
            await session.flush()
            log = AIUsageLog(
                bot_id=bot.id,
                conversation_id=conv.id,
                message_id=msg.id,
                provider_name="openai",
                model_name="gpt-4o-mini",
            )
            session.add(log)
            await session.commit()
            log_id = log.id

            await session.delete(msg)
            await session.commit()

        async with sm() as session:
            reloaded = await session.get(AIUsageLog, log_id)
            assert reloaded is not None
            assert reloaded.message_id is None
            assert reloaded.conversation_id is not None

            owner = await session.scalar(select(User).where(User.email == owner_email))
            assert owner is not None
            await session.delete(owner)
            await session.commit()

    _run_async_db(live_db_url, monkeypatch, body())


def test_foreign_key_rejects_invalid_bot_on_conversation(live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    owner_email = _unique_email("bad-fk-bot")
    fake_bot_id = uuid.uuid4()

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
                Conversation(
                    bot_id=fake_bot_id,
                    owner_id=owner.id,
                    status="active",
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


def test_daily_aggregation_refresh_from_usage_logs(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Materialized daily rows match grouped ``ai_usage_logs`` (UTC calendar date)."""
    owner_email = _unique_email("usage-agg")

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
                name="Agg Bot",
                niche_id="education",
                goal_type="support",
                status="active",
            )
            session.add(bot)
            await session.flush()

            conv = Conversation(
                bot_id=bot.id,
                owner_id=owner.id,
                channel=None,
                status="active",
            )
            session.add(conv)
            await session.flush()

            # Far-future UTC day avoids collisions with other integration tests on shared DBs.
            day = date(2088, 6, 10)
            session.add_all(
                [
                    AIUsageLog(
                        bot_id=bot.id,
                        conversation_id=conv.id,
                        message_id=None,
                        provider_name="gemini",
                        model_name="flash",
                        tokens_input=1,
                        tokens_output=1,
                        tokens_total=2,
                        latency_ms=100,
                        cost_usd=Decimal("0.00001000"),
                        success=True,
                        error_code=None,
                        created_at=datetime(2088, 6, 10, 8, 0, 0, tzinfo=timezone.utc),
                    ),
                    AIUsageLog(
                        bot_id=bot.id,
                        conversation_id=conv.id,
                        message_id=None,
                        provider_name="gemini",
                        model_name="flash",
                        tokens_input=2,
                        tokens_output=2,
                        tokens_total=4,
                        latency_ms=300,
                        cost_usd=Decimal("0.00002000"),
                        success=False,
                        error_code="x",
                        created_at=datetime(2088, 6, 10, 22, 0, 0, tzinfo=timezone.utc),
                    ),
                    AIUsageLog(
                        bot_id=bot.id,
                        conversation_id=conv.id,
                        message_id=None,
                        provider_name="gemini",
                        model_name="flash",
                        tokens_input=1,
                        tokens_output=0,
                        tokens_total=1,
                        latency_ms=None,
                        cost_usd=None,
                        success=True,
                        error_code=None,
                        created_at=datetime(2088, 6, 11, 1, 0, 0, tzinfo=timezone.utc),
                    ),
                ]
            )
            await session.commit()
            bot_id = bot.id

        await dispose_engine()
        get_settings.cache_clear()

        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        svc = AIUsageAggregationService(get_session_maker())
        n = await svc.refresh_materialized_utc_day(day)
        assert n == 1

        await dispose_engine()
        get_settings.cache_clear()

        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        sm2 = get_session_maker()
        async with sm2() as session:
            row = await session.scalar(
                select(DailyAIUsageAggregate).where(
                    DailyAIUsageAggregate.bot_id == bot_id,
                    DailyAIUsageAggregate.usage_date == day,
                )
            )
            assert row is not None
            assert row.total_requests == 2
            assert row.total_tokens == 6
            assert row.total_cost_usd == Decimal("0.00003000")
            assert row.avg_latency_ms == Decimal("200")

            owner_row = await session.scalar(select(User).where(User.email == owner_email))
            assert owner_row is not None
            await session.delete(owner_row)
            await session.commit()

        await dispose_engine()
        get_settings.cache_clear()

    _run_async_db(live_db_url, monkeypatch, body())


def test_daily_aggregation_groups_by_bot_and_utc_date(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same UTC day, two bots → two materialized rows with independent metrics."""
    owner_email = _unique_email("usage-agg-2bot")

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

            bot_a = Bot(
                owner_id=owner.id,
                name="Bot A",
                niche_id="education",
                goal_type="support",
                status="active",
            )
            bot_b = Bot(
                owner_id=owner.id,
                name="Bot B",
                niche_id="education",
                goal_type="support",
                status="active",
            )
            session.add_all([bot_a, bot_b])
            await session.flush()

            conv_a = Conversation(bot_id=bot_a.id, owner_id=owner.id, status="active")
            conv_b = Conversation(bot_id=bot_b.id, owner_id=owner.id, status="active")
            session.add_all([conv_a, conv_b])
            await session.flush()

            day = date(2088, 7, 1)
            session.add_all(
                [
                    AIUsageLog(
                        bot_id=bot_a.id,
                        conversation_id=conv_a.id,
                        message_id=None,
                        provider_name="g",
                        model_name="m",
                        tokens_total=10,
                        latency_ms=50,
                        cost_usd=Decimal("1.0"),
                        success=True,
                        created_at=datetime(2088, 7, 1, 12, 0, 0, tzinfo=timezone.utc),
                    ),
                    AIUsageLog(
                        bot_id=bot_a.id,
                        conversation_id=conv_a.id,
                        message_id=None,
                        provider_name="g",
                        model_name="m",
                        tokens_total=20,
                        latency_ms=150,
                        cost_usd=Decimal("2.0"),
                        success=True,
                        created_at=datetime(2088, 7, 1, 13, 0, 0, tzinfo=timezone.utc),
                    ),
                    AIUsageLog(
                        bot_id=bot_b.id,
                        conversation_id=conv_b.id,
                        message_id=None,
                        provider_name="g",
                        model_name="m",
                        tokens_total=1000,
                        latency_ms=10,
                        cost_usd=Decimal("0.5"),
                        success=True,
                        created_at=datetime(2088, 7, 1, 14, 0, 0, tzinfo=timezone.utc),
                    ),
                    AIUsageLog(
                        bot_id=bot_b.id,
                        conversation_id=conv_b.id,
                        message_id=None,
                        provider_name="g",
                        model_name="m",
                        tokens_total=1,
                        latency_ms=1,
                        success=True,
                        created_at=datetime(2088, 6, 30, 23, 0, 0, tzinfo=timezone.utc),
                    ),
                ]
            )
            await session.commit()
            aid, bid = bot_a.id, bot_b.id

        await dispose_engine()
        get_settings.cache_clear()
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        n = await AIUsageAggregationService(get_session_maker()).refresh_materialized_utc_day(day)
        assert n == 2

        await dispose_engine()
        get_settings.cache_clear()
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        sm3 = get_session_maker()
        async with sm3() as session:
            rows = (
                await session.scalars(
                    select(DailyAIUsageAggregate)
                    .where(DailyAIUsageAggregate.usage_date == day)
                    .order_by(DailyAIUsageAggregate.bot_id)
                )
            ).all()
            assert len(rows) == 2
            by_bot = {r.bot_id: r for r in rows}
            assert by_bot[aid].total_requests == 2
            assert by_bot[aid].total_tokens == 30
            assert by_bot[aid].total_cost_usd == Decimal("3.0")
            assert by_bot[aid].avg_latency_ms == Decimal("100")

            assert by_bot[bid].total_requests == 1
            assert by_bot[bid].total_tokens == 1000
            assert by_bot[bid].total_cost_usd == Decimal("0.5")
            assert by_bot[bid].avg_latency_ms == Decimal("10")

            owner_row = await session.scalar(select(User).where(User.email == owner_email))
            assert owner_row is not None
            await session.delete(owner_row)
            await session.commit()

        await dispose_engine()
        get_settings.cache_clear()

    _run_async_db(live_db_url, monkeypatch, body())


def test_daily_aggregation_empty_utc_day_writes_no_rows(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refresh for a date with no logs yields zero rollups and removes prior materialization."""
    owner_email = _unique_email("usage-agg-empty")

    async def body() -> None:
        sm = get_session_maker()
        empty_day = date(2088, 5, 5)
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
                name="Lonely Bot",
                niche_id="education",
                goal_type="support",
                status="active",
            )
            session.add(bot)
            await session.flush()
            session.add(
                DailyAIUsageAggregate(
                    bot_id=bot.id,
                    usage_date=empty_day,
                    total_requests=99,
                    total_tokens=999,
                    total_cost_usd=Decimal("9"),
                    avg_latency_ms=Decimal("1"),
                )
            )
            await session.commit()

        await dispose_engine()
        get_settings.cache_clear()
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        n = await AIUsageAggregationService(get_session_maker()).refresh_materialized_utc_day(empty_day)
        assert n == 0

        await dispose_engine()
        get_settings.cache_clear()
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        sm4 = get_session_maker()
        async with sm4() as session:
            stale = (
                await session.scalars(
                    select(DailyAIUsageAggregate).where(DailyAIUsageAggregate.usage_date == empty_day)
                )
            ).all()
            assert len(stale) == 0

            owner_row = await session.scalar(select(User).where(User.email == owner_email))
            assert owner_row is not None
            await session.delete(owner_row)
            await session.commit()

        await dispose_engine()
        get_settings.cache_clear()

    _run_async_db(live_db_url, monkeypatch, body())


def test_daily_aggregation_includes_failed_requests_in_totals(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failures are counted like successes; tokens/cost/latency aggregate from log fields."""
    owner_email = _unique_email("usage-agg-fail")

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
                name="Fail Bot",
                niche_id="education",
                goal_type="support",
                status="active",
            )
            session.add(bot)
            await session.flush()
            conv = Conversation(bot_id=bot.id, owner_id=owner.id, status="active")
            session.add(conv)
            await session.flush()

            day = date(2088, 8, 15)
            session.add_all(
                [
                    AIUsageLog(
                        bot_id=bot.id,
                        conversation_id=conv.id,
                        message_id=None,
                        provider_name="g",
                        model_name="m",
                        tokens_total=7,
                        latency_ms=40,
                        cost_usd=None,
                        success=False,
                        error_code="timeout",
                        created_at=datetime(2088, 8, 15, 9, 0, 0, tzinfo=timezone.utc),
                    ),
                    AIUsageLog(
                        bot_id=bot.id,
                        conversation_id=conv.id,
                        message_id=None,
                        provider_name="g",
                        model_name="m",
                        tokens_total=3,
                        latency_ms=60,
                        cost_usd=Decimal("0.02"),
                        success=False,
                        error_code="429",
                        created_at=datetime(2088, 8, 15, 10, 0, 0, tzinfo=timezone.utc),
                    ),
                ]
            )
            await session.commit()
            bot_id = bot.id

        await dispose_engine()
        get_settings.cache_clear()
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        n = await AIUsageAggregationService(get_session_maker()).refresh_materialized_utc_day(day)
        assert n == 1

        await dispose_engine()
        get_settings.cache_clear()
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        sm5 = get_session_maker()
        async with sm5() as session:
            row = await session.scalar(
                select(DailyAIUsageAggregate).where(
                    DailyAIUsageAggregate.bot_id == bot_id,
                    DailyAIUsageAggregate.usage_date == day,
                )
            )
            assert row is not None
            assert row.total_requests == 2
            assert row.total_tokens == 10
            assert row.total_cost_usd == Decimal("0.02")
            assert row.avg_latency_ms == Decimal("50")

            owner_row = await session.scalar(select(User).where(User.email == owner_email))
            assert owner_row is not None
            await session.delete(owner_row)
            await session.commit()

        await dispose_engine()
        get_settings.cache_clear()

    _run_async_db(live_db_url, monkeypatch, body())
