"""PostgreSQL: owner monthly token sum across bots (AIUsageAggregateRepository)."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.models.ai_foundation import AIUsageLog, Conversation
from app.models.bot import Bot
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.ai_usage_aggregate_repository import AIUsageAggregateRepository

from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _db_url(),
        reason="Set TEST_DATABASE_URL or host-reachable DATABASE_URL for integration tests.",
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
def _alembic() -> None:
    u = _db_url()
    assert u is not None
    _alembic_upgrade_head(u)


@pytest.fixture
def live_db_url() -> str:
    u = _db_url()
    assert u is not None
    return u


def test_owner_monthly_sum_counts_only_that_month_utc(live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        owner_id = uuid.uuid4()
        bot_a = uuid.uuid4()
        bot_b = uuid.uuid4()
        conv_a = uuid.uuid4()
        conv_b = uuid.uuid4()
        sm = get_session_maker()
        async with sm() as session:
            session.add(
                User(
                    id=owner_id,
                    email=f"owner_{uuid.uuid4().hex}@example.com",
                    password_hash="x",
                    role=UserRole.customer_admin,
                )
            )
            session.add(Bot(id=bot_a, owner_id=owner_id, name="A", niche_id="n", status="active", goal_type="faq"))
            session.add(Bot(id=bot_b, owner_id=owner_id, name="B", niche_id="n", status="active", goal_type="faq"))
            session.add(
                Conversation(id=conv_a, bot_id=bot_a, owner_id=owner_id, channel=None, status="active")
            )
            session.add(
                Conversation(id=conv_b, bot_id=bot_b, owner_id=owner_id, channel=None, status="active")
            )
            await session.flush()
            ts_jan = datetime(2030, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
            ts_feb = datetime(2030, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
            session.add_all(
                [
                    AIUsageLog(
                        bot_id=bot_a,
                        conversation_id=conv_a,
                        message_id=None,
                        provider_name="g",
                        model_name="m",
                        tokens_total=100,
                        tokens_input=0,
                        tokens_output=0,
                        latency_ms=1,
                        cost_usd=Decimal("0"),
                        success=True,
                        created_at=ts_jan,
                    ),
                    AIUsageLog(
                        bot_id=bot_b,
                        conversation_id=conv_b,
                        message_id=None,
                        provider_name="g",
                        model_name="m",
                        tokens_total=50,
                        tokens_input=0,
                        tokens_output=0,
                        latency_ms=1,
                        cost_usd=Decimal("0"),
                        success=True,
                        created_at=ts_jan,
                    ),
                    AIUsageLog(
                        bot_id=bot_a,
                        conversation_id=conv_a,
                        message_id=None,
                        provider_name="g",
                        model_name="m",
                        tokens_total=999,
                        tokens_input=0,
                        tokens_output=0,
                        latency_ms=1,
                        cost_usd=Decimal("0"),
                        success=True,
                        created_at=ts_feb,
                    ),
                ]
            )
            await session.commit()

            repo = AIUsageAggregateRepository(session)
            s_jan = await repo.sum_tokens_total_for_owner_in_utc_month(owner_id, year=2030, month=1)
            s_feb = await repo.sum_tokens_total_for_owner_in_utc_month(owner_id, year=2030, month=2)
            assert s_jan == 150
            assert s_feb == 999

            urow = await session.get(User, owner_id)
            if urow:
                await session.delete(urow)
                await session.commit()

        await dispose_engine()
        get_settings.cache_clear()

    asyncio.run(body())
