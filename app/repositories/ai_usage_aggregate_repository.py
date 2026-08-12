"""Read :class:`~app.models.ai_foundation.AIUsageLog` and materialize :class:`~app.models.ai_foundation.DailyAIUsageAggregate`."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, cast, delete, extract, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.ai_foundation import AIUsageLog, DailyAIUsageAggregate
from app.models.bot import Bot
from app.schemas.ai_usage import DailyBotUsageRollup


def _utc_calendar_date(column: ColumnElement) -> ColumnElement:
    """PostgreSQL: calendar date in UTC for ``timestamptz`` (see aggregation service docstring)."""
    return cast(func.timezone(text("'UTC'"), column), Date)


class AIUsageAggregateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def compute_daily_rollups_utc(self, usage_date: date) -> list[DailyBotUsageRollup]:
        """
        Aggregate all usage logs whose ``created_at`` falls on ``usage_date`` in UTC.
        """
        day_expr = _utc_calendar_date(AIUsageLog.created_at)
        stmt = (
            select(
                AIUsageLog.bot_id,
                func.count(AIUsageLog.id).label("total_requests"),
                func.coalesce(func.sum(AIUsageLog.tokens_total), 0).label("total_tokens"),
                func.coalesce(func.sum(AIUsageLog.cost_usd), 0).label("total_cost_usd"),
                func.avg(AIUsageLog.latency_ms).label("avg_latency_ms"),
            )
            .where(day_expr == usage_date)
            .group_by(AIUsageLog.bot_id)
        )
        result = await self._session.execute(stmt)
        out: list[DailyBotUsageRollup] = []
        for row in result:
            bot_id = row.bot_id
            assert isinstance(bot_id, uuid.UUID)
            tr = int(row.total_requests)
            tt = int(row.total_tokens)
            tc = row.total_cost_usd
            if tc is None:
                tc_d = Decimal("0")
            else:
                tc_d = tc if isinstance(tc, Decimal) else Decimal(str(tc))
            al = row.avg_latency_ms
            al_d: Decimal | None
            if al is None:
                al_d = None
            else:
                al_d = al if isinstance(al, Decimal) else Decimal(str(al))
            out.append(
                DailyBotUsageRollup(
                    bot_id=bot_id,
                    usage_date=usage_date,
                    total_requests=tr,
                    total_tokens=tt,
                    total_cost_usd=tc_d,
                    avg_latency_ms=al_d,
                )
            )
        return out

    async def replace_materialized_day(self, usage_date: date, rollups: list[DailyBotUsageRollup]) -> None:
        """
        Replace stored aggregates for ``usage_date`` with ``rollups`` (source of truth is ``ai_usage_logs``).
        Does not commit the session.
        """
        await self._session.execute(
            delete(DailyAIUsageAggregate).where(DailyAIUsageAggregate.usage_date == usage_date)
        )
        for r in rollups:
            self._session.add(
                DailyAIUsageAggregate(
                    bot_id=r.bot_id,
                    usage_date=r.usage_date,
                    total_requests=r.total_requests,
                    total_tokens=r.total_tokens,
                    total_cost_usd=r.total_cost_usd,
                    avg_latency_ms=r.avg_latency_ms,
                )
            )
        await self._session.flush()

    async def sum_tokens_total_for_bot_on_utc_date(self, bot_id: uuid.UUID, usage_date: date) -> int:
        """
        Sum ``tokens_total`` (treating NULL as 0) for ``bot_id`` on ``usage_date`` in the UTC calendar.

        Used for MVP soft per-bot daily caps (source table: ``ai_usage_logs``).
        """
        day_expr = _utc_calendar_date(AIUsageLog.created_at)
        stmt = (
            select(func.coalesce(func.sum(func.coalesce(AIUsageLog.tokens_total, 0)), 0))
            .where(AIUsageLog.bot_id == bot_id)
            .where(day_expr == usage_date)
        )
        result = await self._session.execute(stmt)
        val = result.scalar_one()
        return int(val or 0)

    async def sum_tokens_total_for_owner_in_utc_month(
        self,
        owner_id: uuid.UUID,
        *,
        year: int,
        month: int,
    ) -> int:
        """
        Sum ``tokens_total`` for all ``ai_usage_logs`` rows whose ``created_at`` falls in the given
        UTC calendar month, for bots owned by ``owner_id``.
        """
        utc_created = func.timezone(text("'UTC'"), AIUsageLog.created_at)
        stmt = (
            select(func.coalesce(func.sum(func.coalesce(AIUsageLog.tokens_total, 0)), 0))
            .select_from(AIUsageLog)
            .join(Bot, Bot.id == AIUsageLog.bot_id)
            .where(Bot.owner_id == owner_id)
            .where(extract("year", utc_created) == year)
            .where(extract("month", utc_created) == month)
        )
        result = await self._session.execute(stmt)
        val = result.scalar_one()
        return int(val or 0)
