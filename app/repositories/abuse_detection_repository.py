"""Abuse / high-usage detection queries (Feature 12)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_foundation import AIUsageLog, DailyAIUsageAggregate
from app.models.bot import Bot
from app.models.user import User


@dataclass(slots=True)
class AbuseUserRow:
    owner_id: str
    owner_email: str
    total_calls: int
    failed_calls: int
    total_tokens: int
    total_cost_usd: Decimal
    error_rate: float  # 0–1


@dataclass(slots=True)
class ErrorRateRow:
    owner_id: str
    owner_email: str
    error_code: str
    occurrences: int


class AbuseDetectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def high_usage_users(
        self,
        *,
        threshold_calls: int = 500,
        days: int = 1,
        limit: int = 50,
    ) -> list[AbuseUserRow]:
        """Users whose aggregate call count exceeds threshold in the past N days."""
        since = datetime.now(UTC) - timedelta(days=days)

        # Sum DailyAIUsageAggregate per owner (via bot join)
        agg = (
            select(
                Bot.owner_id.label("owner_id"),
                func.sum(DailyAIUsageAggregate.total_requests).label("total_calls"),
                func.sum(DailyAIUsageAggregate.total_tokens).label("total_tokens"),
                func.sum(DailyAIUsageAggregate.total_cost_usd).label("total_cost_usd"),
            )
            .join(Bot, DailyAIUsageAggregate.bot_id == Bot.id)
            .where(DailyAIUsageAggregate.usage_date >= func.date(since))
            .group_by(Bot.owner_id)
            .having(func.sum(DailyAIUsageAggregate.total_requests) >= threshold_calls)
            .subquery()
        )

        # Count failures from raw logs for the same window
        fail_agg = (
            select(
                Bot.owner_id.label("owner_id"),
                func.count(AIUsageLog.id).label("failed_calls"),
            )
            .join(Bot, AIUsageLog.bot_id == Bot.id)
            .where(AIUsageLog.success.is_(False))
            .where(AIUsageLog.created_at >= since)
            .group_by(Bot.owner_id)
            .subquery()
        )

        stmt = (
            select(
                User.id.label("owner_id"),
                User.email.label("owner_email"),
                agg.c.total_calls,
                func.coalesce(fail_agg.c.failed_calls, 0).label("failed_calls"),
                agg.c.total_tokens,
                agg.c.total_cost_usd,
            )
            .join(agg, User.id == agg.c.owner_id)
            .outerjoin(fail_agg, User.id == fail_agg.c.owner_id)
            .order_by(agg.c.total_calls.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        result = []
        for r in rows:
            tc = int(r.total_calls or 0)
            fc = int(r.failed_calls or 0)
            error_rate = round(fc / tc, 4) if tc > 0 else 0.0
            result.append(
                AbuseUserRow(
                    owner_id=str(r.owner_id),
                    owner_email=r.owner_email,
                    total_calls=tc,
                    failed_calls=fc,
                    total_tokens=int(r.total_tokens or 0),
                    total_cost_usd=Decimal(str(r.total_cost_usd or 0)),
                    error_rate=error_rate,
                )
            )
        return result

    async def top_error_codes(
        self,
        *,
        days: int = 7,
        limit: int = 20,
    ) -> list[ErrorRateRow]:
        """Most frequent error codes per owner in the past N days."""
        since = datetime.now(UTC) - timedelta(days=days)
        stmt = (
            select(
                Bot.owner_id.label("owner_id"),
                User.email.label("owner_email"),
                AIUsageLog.error_code.label("error_code"),
                func.count(AIUsageLog.id).label("occurrences"),
            )
            .join(Bot, AIUsageLog.bot_id == Bot.id)
            .join(User, Bot.owner_id == User.id)
            .where(AIUsageLog.success.is_(False))
            .where(AIUsageLog.error_code.is_not(None))
            .where(AIUsageLog.created_at >= since)
            .group_by(Bot.owner_id, User.email, AIUsageLog.error_code)
            .order_by(func.count(AIUsageLog.id).desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            ErrorRateRow(
                owner_id=str(r.owner_id),
                owner_email=r.owner_email,
                error_code=r.error_code,
                occurrences=int(r.occurrences),
            )
            for r in rows
        ]
