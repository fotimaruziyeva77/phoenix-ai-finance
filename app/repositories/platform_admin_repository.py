"""Unscoped read queries for superadmin platform overview (list/search only)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import case, exists, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.telegram_channel_status import TELEGRAM_PROVISIONING_ACTIVE
from app.models.ai_foundation import AIUsageLog, Conversation, DailyAIUsageAggregate
from app.models.bot import Bot
from app.models.lead import Lead
from app.models.enums import UserRole
from app.models.subscription import Subscription
from app.models.telegram_config import TelegramConfig
from app.models.user import OAuthAccount, User
from app.models.widget_config import WidgetConfig


@dataclass(slots=True)
class PlatformUserListFilters:
    role: UserRole | None = None
    is_active: bool | None = None
    search: str | None = None


@dataclass(slots=True)
class PlatformBillingListFilters:
    status: str | None = None  # active | trialing | past_due | canceled | expired
    plan_slug: str | None = None


@dataclass(slots=True)
class PlatformBotListFilters:
    owner_id: uuid.UUID | None = None
    niche_id: str | None = None
    status: str | None = None
    has_widget: bool | None = None
    has_telegram_connected: bool | None = None
    platform_suspended: bool | None = None
    search: str | None = None


class PlatformAdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _user_where_clauses(filters: PlatformUserListFilters) -> list:
        clauses = []
        if filters.role is not None:
            clauses.append(User.role == filters.role)
        if filters.is_active is not None:
            clauses.append(User.is_active == filters.is_active)
        if filters.search is not None and (q := filters.search.strip()):
            pattern = f"%{q}%"
            clauses.append(
                or_(User.email.ilike(pattern), User.full_name.ilike(pattern))
            )
        return clauses

    @staticmethod
    def _bot_where_clauses(filters: PlatformBotListFilters) -> list:
        clauses: list = []
        if filters.owner_id is not None:
            clauses.append(Bot.owner_id == filters.owner_id)
        if filters.niche_id is not None and (n := filters.niche_id.strip()):
            clauses.append(Bot.niche_id == n)
        if filters.status is not None and (s := filters.status.strip()):
            clauses.append(Bot.status == s)
        if filters.platform_suspended is True:
            clauses.append(Bot.platform_suspended_at.is_not(None))
        elif filters.platform_suspended is False:
            clauses.append(Bot.platform_suspended_at.is_(None))

        if filters.has_widget is True:
            clauses.append(
                select(WidgetConfig.id).where(WidgetConfig.bot_id == Bot.id).exists(),
            )
        elif filters.has_widget is False:
            clauses.append(
                ~select(WidgetConfig.id).where(WidgetConfig.bot_id == Bot.id).exists(),
            )

        if filters.has_telegram_connected is True:
            clauses.append(
                select(TelegramConfig.id)
                .where(
                    TelegramConfig.bot_id == Bot.id,
                    TelegramConfig.is_connected.is_(True),
                    TelegramConfig.provisioning_status == TELEGRAM_PROVISIONING_ACTIVE,
                )
                .exists(),
            )
        elif filters.has_telegram_connected is False:
            clauses.append(
                ~select(TelegramConfig.id)
                .where(
                    TelegramConfig.bot_id == Bot.id,
                    TelegramConfig.is_connected.is_(True),
                    TelegramConfig.provisioning_status == TELEGRAM_PROVISIONING_ACTIVE,
                )
                .exists(),
            )

        if filters.search is not None and (q := filters.search.strip()):
            pattern = f"%{q}%"
            clauses.append(
                or_(
                    Bot.name.ilike(pattern),
                    select(User.id).where(User.id == Bot.owner_id, User.email.ilike(pattern)).exists(),
                )
            )

        return clauses

    async def count_users(self, filters: PlatformUserListFilters) -> int:
        stmt = select(func.count(User.id))
        for c in self._user_where_clauses(filters):
            stmt = stmt.where(c)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def list_users_with_counts(
        self,
        *,
        filters: PlatformUserListFilters,
        limit: int,
        offset: int,
    ) -> list[tuple[User, int, int]]:
        # Pre-aggregate counts once per table instead of correlated scalar subqueries per row
        # (avoids repeated Seq Scan + SubPlan on large ``users`` pages).
        bot_counts = (
            select(Bot.owner_id.label("uid"), func.count(Bot.id).label("bot_cnt"))
            .group_by(Bot.owner_id)
            .subquery()
        )
        oauth_counts = (
            select(OAuthAccount.user_id.label("uid"), func.count(OAuthAccount.id).label("oauth_cnt"))
            .group_by(OAuthAccount.user_id)
            .subquery()
        )
        bc = func.coalesce(bot_counts.c.bot_cnt, 0)
        oc = func.coalesce(oauth_counts.c.oauth_cnt, 0)
        stmt = (
            select(User, bc, oc)
            .outerjoin(bot_counts, User.id == bot_counts.c.uid)
            .outerjoin(oauth_counts, User.id == oauth_counts.c.uid)
            .order_by(User.created_at.desc())
            .offset(max(offset, 0))
            .limit(min(max(limit, 1), 200))
        )
        for c in self._user_where_clauses(filters):
            stmt = stmt.where(c)
        result = await self._session.execute(stmt)
        out: list[tuple[User, int, int]] = []
        for row in result.all():
            u, bot_c, oauth_c = row[0], int(row[1] or 0), int(row[2] or 0)
            out.append((u, bot_c, oauth_c))
        return out

    async def get_user_with_oauth(self, user_id: uuid.UUID) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.oauth_accounts))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_bots_for_owner(self, owner_id: uuid.UUID) -> int:
        stmt = select(func.count(Bot.id)).where(Bot.owner_id == owner_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def count_bots(self, filters: PlatformBotListFilters) -> int:
        stmt = select(func.count(Bot.id)).select_from(Bot).join(User, User.id == Bot.owner_id)
        for c in self._bot_where_clauses(filters):
            stmt = stmt.where(c)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def list_bots_with_overview(
        self,
        *,
        filters: PlatformBotListFilters,
        limit: int,
        offset: int,
    ) -> list[tuple[Bot, str, bool, bool]]:
        has_widget_sq = exists(select(1).where(WidgetConfig.bot_id == Bot.id))
        has_telegram_sq = exists(
            select(1).where(
                TelegramConfig.bot_id == Bot.id,
                TelegramConfig.is_connected.is_(True),
                TelegramConfig.provisioning_status == TELEGRAM_PROVISIONING_ACTIVE,
            )
        )
        stmt = (
            select(Bot, User.email, has_widget_sq, has_telegram_sq)
            .join(User, User.id == Bot.owner_id)
            .order_by(Bot.updated_at.desc())
            .offset(max(offset, 0))
            .limit(min(max(limit, 1), 200))
        )
        for c in self._bot_where_clauses(filters):
            stmt = stmt.where(c)
        result = await self._session.execute(stmt)
        out: list[tuple[Bot, str, bool, bool]] = []
        for row in result.all():
            b, em, hw, ht = row[0], str(row[1]), bool(row[2]), bool(row[3])
            out.append((b, em, hw, ht))
        return out

    async def widget_row_count_for_bot(self, bot_id: uuid.UUID) -> int:
        stmt = select(func.count(WidgetConfig.id)).where(WidgetConfig.bot_id == bot_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def telegram_connected_for_bot(self, bot_id: uuid.UUID) -> bool:
        stmt = (
            select(TelegramConfig.is_connected)
            .where(
                TelegramConfig.bot_id == bot_id,
                TelegramConfig.provisioning_status == TELEGRAM_PROVISIONING_ACTIVE,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.first()
        if row is None:
            return False
        return bool(row[0])

    async def get_bot_unscoped(self, bot_id: uuid.UUID) -> Bot | None:
        stmt = select(Bot).where(Bot.id == bot_id).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_owner_email(self, owner_id: uuid.UUID) -> str | None:
        stmt = select(User.email).where(User.id == owner_id).limit(1)
        result = await self._session.execute(stmt)
        row = result.first()
        return str(row[0]) if row else None

    async def count_leads_for_owner(self, owner_id: uuid.UUID) -> int:
        stmt = select(func.count(Lead.id)).where(Lead.owner_id == owner_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def count_conversations_for_owner(self, owner_id: uuid.UUID) -> int:
        stmt = select(func.count(Conversation.id)).where(Conversation.owner_id == owner_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def conversation_channel_breakdown_for_owner(self, owner_id: uuid.UUID) -> list[tuple[str, int]]:
        ch = func.coalesce(Conversation.channel, literal("legacy"))
        cnt = func.count(Conversation.id)
        stmt = (
            select(ch, cnt)
            .where(Conversation.owner_id == owner_id)
            .group_by(ch)
            .order_by(cnt.desc())
        )
        result = await self._session.execute(stmt)
        return [(str(r[0]), int(r[1] or 0)) for r in result.all()]

    async def ai_usage_stats_for_owner_since(
        self,
        owner_id: uuid.UUID,
        since: datetime,
    ) -> tuple[int, int, int, int]:
        """
        Returns (total_calls, success_calls, failed_calls, total_tokens) for the owner's bots.
        """
        fail_sum = func.coalesce(
            func.sum(case((AIUsageLog.success.is_(False), 1), else_=0)),
            0,
        )
        ok_sum = func.coalesce(
            func.sum(case((AIUsageLog.success.is_(True), 1), else_=0)),
            0,
        )
        tok_sum = func.coalesce(func.sum(AIUsageLog.tokens_total), 0)
        stmt = (
            select(func.count(AIUsageLog.id), ok_sum, fail_sum, tok_sum)
            .select_from(AIUsageLog)
            .join(Bot, Bot.id == AIUsageLog.bot_id)
            .where(Bot.owner_id == owner_id, AIUsageLog.created_at >= since)
        )
        result = await self._session.execute(stmt)
        row = result.one()
        total = int(row[0] or 0)
        ok_c = int(row[1] or 0)
        fail_c = int(row[2] or 0)
        tokens = int(row[3] or 0)
        return total, ok_c, fail_c, tokens

    async def recent_ai_failures_for_owner(
        self,
        owner_id: uuid.UUID,
        *,
        limit: int = 20,
    ) -> list[tuple[datetime, uuid.UUID, str, str | None]]:
        stmt = (
            select(AIUsageLog.created_at, AIUsageLog.bot_id, AIUsageLog.model_name, AIUsageLog.error_code)
            .select_from(AIUsageLog)
            .join(Bot, Bot.id == AIUsageLog.bot_id)
            .where(Bot.owner_id == owner_id, AIUsageLog.success.is_(False))
            .order_by(AIUsageLog.created_at.desc())
            .limit(min(max(limit, 1), 50))
        )
        result = await self._session.execute(stmt)
        return [(r[0], r[1], str(r[2]), r[3]) for r in result.all()]

    async def get_platform_stats(self) -> dict[str, object]:
        """
        Aggregate platform-wide counts for the superadmin stats endpoint.

        Returns a dict with keys:
          total_users, active_users, total_bots, active_bots,
          total_leads, total_conversations,
          subscription_distribution (list of (plan_slug, count) tuples)
        """
        # User counts
        total_users_result = await self._session.execute(select(func.count(User.id)))
        total_users = int(total_users_result.scalar_one() or 0)

        active_users_result = await self._session.execute(
            select(func.count(User.id)).where(User.is_active.is_(True))
        )
        active_users = int(active_users_result.scalar_one() or 0)

        # Bot counts
        total_bots_result = await self._session.execute(select(func.count(Bot.id)))
        total_bots = int(total_bots_result.scalar_one() or 0)

        active_bots_result = await self._session.execute(
            select(func.count(Bot.id)).where(Bot.status == "active")
        )
        active_bots = int(active_bots_result.scalar_one() or 0)

        # Lead + conversation counts
        total_leads_result = await self._session.execute(select(func.count(Lead.id)))
        total_leads = int(total_leads_result.scalar_one() or 0)

        total_conv_result = await self._session.execute(select(func.count(Conversation.id)))
        total_conversations = int(total_conv_result.scalar_one() or 0)

        # Subscription distribution (plan_slug → count)
        dist_result = await self._session.execute(
            select(Subscription.plan_slug, func.count(Subscription.id))
            .group_by(Subscription.plan_slug)
            .order_by(func.count(Subscription.id).desc())
        )
        subscription_distribution = [(str(row[0].value if hasattr(row[0], 'value') else row[0]), int(row[1])) for row in dist_result.all()]

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_bots": total_bots,
            "active_bots": active_bots,
            "total_leads": total_leads,
            "total_conversations": total_conversations,
            "subscription_distribution": subscription_distribution,
        }

    # ------------------------------------------------------------------
    # Billing queries
    # ------------------------------------------------------------------

    # Plan prices in USD/month (mirrors frontend pricing-data.ts)
    _PLAN_PRICES: dict[str, float] = {
        "free": 0.0,
        "pro": 39.0,
        "business": 99.0,
        "enterprise": 0.0,
    }

    async def count_billing(self, filters: "PlatformBillingListFilters") -> int:
        stmt = select(func.count(Subscription.id)).select_from(Subscription)
        if filters.status:
            stmt = stmt.where(Subscription.status == filters.status)
        if filters.plan_slug:
            stmt = stmt.where(Subscription.plan_slug == filters.plan_slug)
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def list_billing(
        self,
        *,
        filters: "PlatformBillingListFilters",
        limit: int,
        offset: int,
    ) -> list[tuple]:
        stmt = (
            select(
                Subscription,
                User.email,
                User.full_name,
                User.is_active,
            )
            .join(User, User.id == Subscription.user_id)
            .order_by(Subscription.updated_at.desc())
            .offset(max(offset, 0))
            .limit(min(max(limit, 1), 200))
        )
        if filters.status:
            stmt = stmt.where(Subscription.status == filters.status)
        if filters.plan_slug:
            stmt = stmt.where(Subscription.plan_slug == filters.plan_slug)
        result = await self._session.execute(stmt)
        return list(result.all())

    async def get_billing_stats(self) -> dict[str, object]:
        """MRR + status counts for dashboard billing KPIs."""
        dist_result = await self._session.execute(
            select(Subscription.plan_slug, Subscription.status, func.count(Subscription.id))
            .group_by(Subscription.plan_slug, Subscription.status)
        )
        rows = dist_result.all()

        mrr = 0.0
        paid_active = 0
        free_count = 0
        past_due = 0
        canceled = 0
        expired = 0

        for row in rows:
            plan = str(row[0].value if hasattr(row[0], "value") else row[0])
            status = str(row[1].value if hasattr(row[1], "value") else row[1])
            count = int(row[2] or 0)
            price = self._PLAN_PRICES.get(plan, 0.0)

            if plan == "free":
                free_count += count
            elif status in ("active", "trialing"):
                mrr += price * count
                paid_active += count

            if status == "past_due":
                past_due += count
            elif status == "canceled":
                canceled += count
            elif status == "expired":
                expired += count

        return {
            "mrr_usd": round(mrr, 2),
            "total_paid_active": paid_active,
            "total_free": free_count,
            "total_past_due": past_due,
            "total_canceled": canceled,
            "total_expired": expired,
        }

    # ------------------------------------------------------------------
    # Platform-wide AI usage (admin monitor)
    # ------------------------------------------------------------------

    async def platform_ai_usage_stats(
        self,
        *,
        days: int = 30,
    ) -> dict[str, object]:
        """Total AI call stats across ALL bots for the last ``days`` days."""
        d = min(max(days, 1), 90)
        since = datetime.now(tz=UTC) - timedelta(days=d)

        fail_sum = func.coalesce(
            func.sum(case((AIUsageLog.success.is_(False), 1), else_=0)), 0
        )
        ok_sum = func.coalesce(
            func.sum(case((AIUsageLog.success.is_(True), 1), else_=0)), 0
        )
        tok_sum = func.coalesce(func.sum(AIUsageLog.tokens_total), 0)
        cost_sum = func.coalesce(func.sum(AIUsageLog.cost_usd), Decimal("0"))

        stmt = select(
            func.count(AIUsageLog.id),
            ok_sum,
            fail_sum,
            tok_sum,
            cost_sum,
        ).where(AIUsageLog.created_at >= since)

        result = await self._session.execute(stmt)
        row = result.one()
        total = int(row[0] or 0)
        ok_c = int(row[1] or 0)
        fail_c = int(row[2] or 0)
        tokens = int(row[3] or 0)
        cost = float(row[4] or 0)
        return {
            "period_days": d,
            "total_calls": total,
            "successful_calls": ok_c,
            "failed_calls": fail_c,
            "total_tokens": tokens,
            "total_cost_usd": round(cost, 6),
            "success_rate": round(ok_c / total, 4) if total > 0 else 1.0,
        }

    async def platform_daily_ai_usage(
        self,
        *,
        days: int = 30,
    ) -> list[tuple[date, int, int, Decimal]]:
        """Per-calendar-day totals across ALL bots for the last ``days`` days."""
        d = min(max(days, 1), 90)
        cutoff = datetime.now(tz=UTC).date() - timedelta(days=d - 1)

        req = func.coalesce(func.sum(DailyAIUsageAggregate.total_requests), 0)
        tok = func.coalesce(func.sum(DailyAIUsageAggregate.total_tokens), 0)
        cost = func.coalesce(func.sum(DailyAIUsageAggregate.total_cost_usd), Decimal("0"))

        stmt = (
            select(DailyAIUsageAggregate.usage_date, req, tok, cost)
            .where(DailyAIUsageAggregate.usage_date >= cutoff)
            .group_by(DailyAIUsageAggregate.usage_date)
            .order_by(DailyAIUsageAggregate.usage_date.asc())
        )
        result = await self._session.execute(stmt)
        return [(r[0], int(r[1] or 0), int(r[2] or 0), r[3]) for r in result.all()]

    async def top_ai_consumers(
        self,
        *,
        days: int = 30,
        limit: int = 10,
    ) -> list[tuple[str, str, int, Decimal, int]]:
        """
        Top users by token consumption over the last ``days`` days.
        Returns list of (owner_id, owner_email, total_tokens, total_cost_usd, total_calls).
        """
        d = min(max(days, 1), 90)
        since = datetime.now(tz=UTC) - timedelta(days=d)
        tok = func.coalesce(func.sum(AIUsageLog.tokens_total), 0).label("total_tokens")
        cost = func.coalesce(func.sum(AIUsageLog.cost_usd), Decimal("0")).label("total_cost")
        calls = func.count(AIUsageLog.id).label("total_calls")

        stmt = (
            select(Bot.owner_id, User.email, tok, cost, calls)
            .select_from(AIUsageLog)
            .join(Bot, Bot.id == AIUsageLog.bot_id)
            .join(User, User.id == Bot.owner_id)
            .where(AIUsageLog.created_at >= since)
            .group_by(Bot.owner_id, User.email)
            .order_by(tok.desc())
            .limit(min(max(limit, 1), 50))
        )
        result = await self._session.execute(stmt)
        return [
            (str(r[0]), str(r[1]), int(r[2] or 0), r[3], int(r[4] or 0))
            for r in result.all()
        ]

    async def daily_ai_usage_rollups_for_owner(
        self,
        owner_id: uuid.UUID,
        *,
        days: int = 7,
    ) -> list[tuple[date, int, int, Decimal]]:
        """Per-calendar-day aggregates summed across the owner's bots (last ``days`` days inclusive)."""
        d = min(max(days, 1), 90)
        cutoff = datetime.now(tz=UTC).date() - timedelta(days=d - 1)
        req = func.coalesce(func.sum(DailyAIUsageAggregate.total_requests), 0)
        tok = func.coalesce(func.sum(DailyAIUsageAggregate.total_tokens), 0)
        cost = func.coalesce(func.sum(DailyAIUsageAggregate.total_cost_usd), Decimal("0"))
        stmt = (
            select(DailyAIUsageAggregate.usage_date, req, tok, cost)
            .select_from(DailyAIUsageAggregate)
            .join(Bot, Bot.id == DailyAIUsageAggregate.bot_id)
            .where(Bot.owner_id == owner_id, DailyAIUsageAggregate.usage_date >= cutoff)
            .group_by(DailyAIUsageAggregate.usage_date)
            .order_by(DailyAIUsageAggregate.usage_date.asc())
        )
        result = await self._session.execute(stmt)
        return [(r[0], int(r[1] or 0), int(r[2] or 0), r[3]) for r in result.all()]
