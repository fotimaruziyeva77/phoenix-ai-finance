"""Unit tests for aggregation orchestration (SQL rollups covered in integration tests)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.ai_usage import DailyBotUsageRollup
from app.services.ai_usage_aggregation_service import AIUsageAggregationService


def test_refresh_materialized_utc_day_orchestrates_repository_and_commits() -> None:
    """Job entrypoint computes rollups, replaces materialized rows for the date, then commits."""

    async def run() -> None:
        d = date(2026, 1, 2)
        rollups = [
            DailyBotUsageRollup(
                bot_id=uuid.uuid4(),
                usage_date=d,
                total_requests=3,
                total_tokens=100,
                total_cost_usd=Decimal("0.5"),
                avg_latency_ms=Decimal("42.5"),
            )
        ]

        session = AsyncMock()
        session.commit = AsyncMock()

        class _CM:
            def __init__(self, sess: AsyncMock) -> None:
                self._sess = sess

            async def __aenter__(self) -> AsyncMock:
                return self._sess

            async def __aexit__(self, *args: object) -> None:
                return None

        maker = MagicMock(return_value=_CM(session))

        with patch(
            "app.services.ai_usage_aggregation_service.AIUsageAggregateRepository"
        ) as RepoCls:
            inst = RepoCls.return_value
            inst.compute_daily_rollups_utc = AsyncMock(return_value=rollups)
            inst.replace_materialized_day = AsyncMock()

            svc = AIUsageAggregationService(maker)
            n = await svc.refresh_materialized_utc_day(d)

        assert n == 1
        RepoCls.assert_called_once_with(session)
        inst.compute_daily_rollups_utc.assert_awaited_once_with(d)
        inst.replace_materialized_day.assert_awaited_once_with(d, rollups)
        session.commit.assert_awaited_once()
        maker.assert_called_once_with()

    asyncio.run(run())
