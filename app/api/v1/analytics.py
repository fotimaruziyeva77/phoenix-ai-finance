"""Owner-scoped analytics summary endpoint (replaces client-side 200-lead aggregation)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import BillingServiceDep, CurrentUser, DbSession
from app.models.ai_foundation import Conversation
from app.models.bot import Bot
from app.models.lead import Lead
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.plan_limits import get_plan

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ── Response schemas ──────────────────────────────────────────────────────────

class BotStatusBreakdown(BaseModel):
    draft: int = Field(ge=0, default=0)
    active: int = Field(ge=0, default=0)
    paused: int = Field(ge=0, default=0)
    archived: int = Field(ge=0, default=0)
    total: int = Field(ge=0, default=0)


class LeadStatusBreakdown(BaseModel):
    new: int = Field(ge=0, default=0)
    contacted: int = Field(ge=0, default=0)
    qualified: int = Field(ge=0, default=0)
    proposal: int = Field(ge=0, default=0)
    won: int = Field(ge=0, default=0)
    lost: int = Field(ge=0, default=0)
    total: int = Field(ge=0, default=0)


class LeadTemperatureBreakdown(BaseModel):
    hot: int = Field(ge=0, default=0)
    warm: int = Field(ge=0, default=0)
    cold: int = Field(ge=0, default=0)
    unknown: int = Field(ge=0, default=0)


class UsageSummary(BaseModel):
    conversations_this_month: int = Field(ge=0, default=0)
    conversations_limit: int | None = Field(
        default=None,
        description="Monthly conversation limit from active plan; null = unlimited.",
    )
    plan_slug: str = Field(default="free")
    plan_name: str = Field(default="Free")


class AnalyticsSummaryResponse(BaseModel):
    bots: BotStatusBreakdown
    leads: LeadStatusBreakdown
    lead_temperature: LeadTemperatureBreakdown
    usage: UsageSummary
    period_days: int = Field(default=30, ge=7, le=365)
    generated_at: datetime


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _bot_status_breakdown(session: AsyncSession, owner_id: UUID) -> BotStatusBreakdown:
    stmt = (
        select(Bot.status, func.count(Bot.id))
        .where(Bot.owner_id == owner_id)
        .group_by(Bot.status)
    )
    result = await session.execute(stmt)
    counts: dict[str, int] = {str(row[0]): int(row[1]) for row in result.all()}
    total = sum(counts.values())
    return BotStatusBreakdown(
        draft=counts.get("draft", 0),
        active=counts.get("active", 0),
        paused=counts.get("paused", 0),
        archived=counts.get("archived", 0),
        total=total,
    )


async def _lead_status_breakdown(
    session: AsyncSession, owner_id: UUID, since: datetime
) -> LeadStatusBreakdown:
    stmt = (
        select(Lead.status, func.count(Lead.id))
        .where(Lead.owner_id == owner_id, Lead.created_at >= since)
        .group_by(Lead.status)
    )
    result = await session.execute(stmt)
    counts: dict[str, int] = {str(row[0]): int(row[1]) for row in result.all()}
    total = sum(counts.values())
    return LeadStatusBreakdown(
        new=counts.get("new", 0),
        contacted=counts.get("contacted", 0),
        qualified=counts.get("qualified", 0),
        proposal=counts.get("proposal", 0),
        won=counts.get("won", 0),
        lost=counts.get("lost", 0),
        total=total,
    )


async def _lead_temperature_breakdown(
    session: AsyncSession, owner_id: UUID, since: datetime
) -> LeadTemperatureBreakdown:
    temp_col = func.coalesce(Lead.lead_temperature, literal("unknown"))
    stmt = (
        select(temp_col, func.count(Lead.id))
        .where(Lead.owner_id == owner_id, Lead.created_at >= since)
        .group_by(temp_col)
    )
    result = await session.execute(stmt)
    counts: dict[str, int] = {str(row[0]): int(row[1]) for row in result.all()}
    return LeadTemperatureBreakdown(
        hot=counts.get("hot", 0),
        warm=counts.get("warm", 0),
        cold=counts.get("cold", 0),
        unknown=counts.get("unknown", 0),
    )


async def _conversations_this_month(session: AsyncSession, owner_id: UUID) -> int:
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    stmt = (
        select(func.count(Conversation.id))
        .where(
            Conversation.owner_id == owner_id,
            Conversation.created_at >= month_start,
        )
    )
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Analytics summary for the current user's workspace",
)
async def analytics_summary(
    user: CurrentUser,
    session: DbSession,
    billing_service: BillingServiceDep,
    period_days: int = Query(
        default=30,
        ge=7,
        le=365,
        description="Rolling window for lead stats in days (7, 30, or 90 are the UI presets).",
    ),
) -> AnalyticsSummaryResponse:
    """
    Aggregate bot/lead/conversation stats for the authenticated user.
    Lead counts are scoped to the last ``period_days`` days; bot counts are all-time.

    Free-plan users receive bot counts and usage summary only;
    lead breakdowns require a Pro plan or higher.
    """
    now = datetime.now(UTC)
    since = now - timedelta(days=period_days)

    # Subscription plan info
    sub_repo = SubscriptionRepository(session)
    sub = await sub_repo.get_by_user_id(user.id)
    plan_slug = sub.plan_slug.value if sub else "free"
    plan_limits = get_plan(plan_slug)
    conversations_limit: int | None = plan_limits.conversations_per_month

    # Bot counts and conversations are always available
    bots = await _bot_status_breakdown(session, user.id)
    conv_count = await _conversations_this_month(session, user.id)

    # Lead breakdowns gated by plan — Free users get empty breakdowns
    if plan_limits.allows_detailed_analytics():
        leads = await _lead_status_breakdown(session, user.id, since)
        lead_temp = await _lead_temperature_breakdown(session, user.id, since)
    else:
        leads = LeadStatusBreakdown()
        lead_temp = LeadTemperatureBreakdown()

    return AnalyticsSummaryResponse(
        bots=bots,
        leads=leads,
        lead_temperature=lead_temp,
        usage=UsageSummary(
            conversations_this_month=conv_count,
            conversations_limit=conversations_limit,
            plan_slug=plan_slug,
            plan_name=plan_limits.name,
        ),
        period_days=period_days,
        generated_at=now,
    )
