"""
Daily usage rollups for analytics dashboards (materialized from ``ai_usage_logs``).

**UTC calendar day:** Rows are grouped by ``(timezone('UTC', created_at))::date``. Align scheduled
jobs and reporting to UTC, or extend this module with a configurable timezone later.

**Scheduled jobs (future):** Run ``refresh_materialized_utc_day`` once per day after UTC midnight,
e.g. APScheduler, Celery beat, or an external cron hitting a small admin endpoint::

    from datetime import datetime, timedelta, timezone
    from app.core.db import get_session_maker
    from app.services.ai_usage_aggregation_service import AIUsageAggregationService

    async def job() -> None:
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        svc = AIUsageAggregationService(get_session_maker())
        await svc.refresh_materialized_utc_day(yesterday)

Pass ``usage_date=yesterday`` so the closed UTC day is complete. For backfill, call the same
method for each ``date`` in range. The operation is idempotent for a given day (delete + rebuild).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.ai_usage_aggregate_repository import AIUsageAggregateRepository
from app.schemas.ai_usage import DailyBotUsageRollup


class AIUsageAggregationService:
    """Job-ready orchestration: compute rollups from logs and write ``daily_ai_usage_aggregates``."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def compute_rollups_utc_day(self, session: AsyncSession, usage_date: date) -> list[DailyBotUsageRollup]:
        """Read-only aggregation; caller manages transaction."""
        repo = AIUsageAggregateRepository(session)
        return await repo.compute_daily_rollups_utc(usage_date)

    async def refresh_materialized_utc_day(self, usage_date: date) -> int:
        """
        Rebuild materialized rows for ``usage_date`` (UTC) and commit.

        Returns the number of bot-level aggregate rows written.
        """
        sm = self._session_maker
        async with sm() as session:
            repo = AIUsageAggregateRepository(session)
            rollups = await repo.compute_daily_rollups_utc(usage_date)
            await repo.replace_materialized_day(usage_date, rollups)
            await session.commit()
        return len(rollups)
