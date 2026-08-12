"""Platform segment analytics queries (Feature 10)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import String, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_foundation import Conversation, DailyAIUsageAggregate
from app.models.bot import Bot
from app.models.subscription import Subscription
from app.models.user import User


@dataclass(slots=True)
class ChannelStat:
    channel: str
    count: int


@dataclass(slots=True)
class NicheStat:
    niche_id: str
    bot_count: int


@dataclass(slots=True)
class GoalTypeStat:
    goal_type: str
    count: int


@dataclass(slots=True)
class ChurnStat:
    plan_slug: str
    canceled_count: int


@dataclass(slots=True)
class SignupTrendRow:
    day: str  # ISO date string
    count: int


@dataclass(slots=True)
class PlanSegmentStat:
    plan_slug: str
    status: str
    count: int


class SegmentAnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def channel_distribution(self, days: int = 30) -> list[ChannelStat]:
        """Conversations per channel in the past N days."""
        since = datetime.now(UTC) - timedelta(days=days)
        stmt = (
            select(Conversation.channel, func.count(Conversation.id).label("cnt"))
            .where(Conversation.created_at >= since)
            .where(Conversation.channel.is_not(None))
            .group_by(Conversation.channel)
            .order_by(func.count(Conversation.id).desc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [ChannelStat(channel=r.channel, count=int(r.cnt)) for r in rows]

    async def niche_distribution(self) -> list[NicheStat]:
        """Active bots grouped by niche."""
        stmt = (
            select(Bot.niche_id, func.count(Bot.id).label("cnt"))
            .where(Bot.niche_id.is_not(None))
            .where(Bot.platform_suspended_at.is_(None))
            .group_by(Bot.niche_id)
            .order_by(func.count(Bot.id).desc())
            .limit(20)
        )
        rows = (await self._session.execute(stmt)).all()
        return [NicheStat(niche_id=r.niche_id, bot_count=int(r.cnt)) for r in rows]

    async def goal_type_distribution(self) -> list[GoalTypeStat]:
        """Bots grouped by goal_type."""
        stmt = (
            select(Bot.goal_type, func.count(Bot.id).label("cnt"))
            .where(Bot.goal_type.is_not(None))
            .group_by(Bot.goal_type)
            .order_by(func.count(Bot.id).desc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [GoalTypeStat(goal_type=r.goal_type, count=int(r.cnt)) for r in rows]

    async def plan_churn_analysis(self) -> list[ChurnStat]:
        """Canceled subscriptions grouped by the plan they were on."""
        stmt = (
            select(
                Subscription.plan_slug.cast(String).label("plan"),
                func.count(Subscription.user_id).label("cnt"),
            )
            .where(Subscription.canceled_at.is_not(None))
            .group_by(Subscription.plan_slug)
            .order_by(func.count(Subscription.user_id).desc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [ChurnStat(plan_slug=str(r.plan), canceled_count=int(r.cnt)) for r in rows]

    async def signup_trend(self, days: int = 30) -> list[SignupTrendRow]:
        """Daily new user signups over the past N days."""
        since = datetime.now(UTC) - timedelta(days=days)
        stmt = (
            select(
                func.date(User.created_at).label("day"),
                func.count(User.id).label("cnt"),
            )
            .where(User.created_at >= since)
            .group_by(func.date(User.created_at))
            .order_by(func.date(User.created_at))
        )
        rows = (await self._session.execute(stmt)).all()
        return [SignupTrendRow(day=str(r.day), count=int(r.cnt)) for r in rows]

    async def plan_segment_breakdown(self) -> list[PlanSegmentStat]:
        """Current subscriptions grouped by plan_slug + status."""
        stmt = (
            select(
                Subscription.plan_slug.cast(String).label("plan_slug"),
                Subscription.status.cast(String).label("status"),
                func.count(Subscription.user_id).label("cnt"),
            )
            .group_by(Subscription.plan_slug, Subscription.status)
            .order_by(Subscription.plan_slug, Subscription.status)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            PlanSegmentStat(plan_slug=str(r.plan_slug), status=str(r.status), count=int(r.cnt))
            for r in rows
        ]
