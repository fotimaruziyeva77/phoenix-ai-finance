"""Superadmin segment & channel analytics (Feature 10)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query

from app.api.deps import RequireSuperadmin, SegmentAnalyticsRepoDep
from pydantic import BaseModel

router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])


class SegmentAnalyticsResponse(BaseModel):
    channels: list[dict]
    niches: list[dict]
    goal_types: list[dict]
    churn_by_plan: list[dict]
    signup_trend: list[dict]
    plan_segments: list[dict]
    period_days: int


@router.get(
    "/segments",
    response_model=SegmentAnalyticsResponse,
    summary="Platform segment & channel analytics (superadmin)",
)
async def get_segment_analytics(
    _admin: RequireSuperadmin,
    repo: SegmentAnalyticsRepoDep,
    days: int = Query(default=30, ge=1, le=365),
) -> SegmentAnalyticsResponse:
    # Run all 6 queries in parallel for maximum performance
    channels, niches, goals, churn, trend, plan_segs = await asyncio.gather(
        repo.channel_distribution(days),
        repo.niche_distribution(),
        repo.goal_type_distribution(),
        repo.plan_churn_analysis(),
        repo.signup_trend(days),
        repo.plan_segment_breakdown(),
    )
    return SegmentAnalyticsResponse(
        channels=[{"channel": c.channel, "count": c.count} for c in channels],
        niches=[{"niche_id": n.niche_id, "bot_count": n.bot_count} for n in niches],
        goal_types=[{"goal_type": g.goal_type, "count": g.count} for g in goals],
        churn_by_plan=[{"plan_slug": c.plan_slug, "canceled_count": c.canceled_count} for c in churn],
        signup_trend=[{"day": t.day, "count": t.count} for t in trend],
        plan_segments=[{"plan_slug": p.plan_slug, "status": p.status, "count": p.count} for p in plan_segs],
        period_days=days,
    )
