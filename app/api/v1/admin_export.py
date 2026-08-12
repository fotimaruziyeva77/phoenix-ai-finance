"""Superadmin data export to CSV (Feature 13)."""

from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.deps import DbSession, RequireSuperadmin
from sqlalchemy import select, text
from app.models.user import User
from app.models.subscription import Subscription
from app.models.bot import Bot
from app.models.ai_foundation import DailyAIUsageAggregate
from app.models.coupon import Coupon

router = APIRouter(prefix="/admin/export", tags=["admin-export"])


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid datetime: {s!r}")


def _csv_response(rows: list[list], headers: list[str], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/users.csv", summary="Export all users as CSV (superadmin)")
async def export_users(
    _admin: RequireSuperadmin,
    session: DbSession,
    since: str | None = Query(default=None, description="ISO 8601 lower bound for created_at"),
    until: str | None = Query(default=None, description="ISO 8601 upper bound for created_at"),
) -> StreamingResponse:
    stmt = (
        select(
            User.id, User.email, User.full_name, User.role,
            User.is_active, User.is_verified, User.suspended_at,
            User.created_at, User.updated_at,
        )
        .order_by(User.created_at)
    )
    dt_since = _parse_dt(since)
    dt_until = _parse_dt(until)
    if dt_since:
        stmt = stmt.where(User.created_at >= dt_since)
    if dt_until:
        stmt = stmt.where(User.created_at <= dt_until)
    rows = (await session.execute(stmt)).all()
    data = [
        [
            str(r.id), r.email, r.full_name or "",
            str(r.role.value) if hasattr(r.role, "value") else str(r.role),
            str(r.is_active), str(r.is_verified),
            r.suspended_at.isoformat() if r.suspended_at else "",
            r.created_at.isoformat() if r.created_at else "",
            r.updated_at.isoformat() if r.updated_at else "",
        ]
        for r in rows
    ]
    return _csv_response(
        data,
        ["id", "email", "full_name", "role", "is_active", "is_verified",
         "suspended_at", "created_at", "updated_at"],
        "users.csv",
    )


@router.get("/subscriptions.csv", summary="Export all subscriptions as CSV (superadmin)")
async def export_subscriptions(
    _admin: RequireSuperadmin,
    session: DbSession,
    since: str | None = Query(default=None, description="ISO 8601 lower bound for created_at"),
    until: str | None = Query(default=None, description="ISO 8601 upper bound for created_at"),
) -> StreamingResponse:
    stmt = (
        select(
            Subscription.user_id,
            User.email,
            Subscription.plan_slug,
            Subscription.status,
            Subscription.stripe_customer_id,
            Subscription.stripe_subscription_id,
            Subscription.current_period_start,
            Subscription.current_period_end,
            Subscription.canceled_at,
            Subscription.created_at,
        )
        .join(User, User.id == Subscription.user_id)
        .order_by(Subscription.created_at)
    )
    dt_since = _parse_dt(since)
    dt_until = _parse_dt(until)
    if dt_since:
        stmt = stmt.where(Subscription.created_at >= dt_since)
    if dt_until:
        stmt = stmt.where(Subscription.created_at <= dt_until)
    rows = (await session.execute(stmt)).all()
    data = [
        [
            str(r.user_id), r.email,
            str(r.plan_slug.value) if hasattr(r.plan_slug, "value") else str(r.plan_slug),
            str(r.status.value) if hasattr(r.status, "value") else str(r.status),
            r.stripe_customer_id or "",
            r.stripe_subscription_id or "",
            r.current_period_start.isoformat() if r.current_period_start else "",
            r.current_period_end.isoformat() if r.current_period_end else "",
            r.canceled_at.isoformat() if r.canceled_at else "",
            r.created_at.isoformat() if r.created_at else "",
        ]
        for r in rows
    ]
    return _csv_response(
        data,
        ["user_id", "email", "plan_slug", "status", "stripe_customer_id",
         "stripe_subscription_id", "current_period_start", "current_period_end",
         "canceled_at", "created_at"],
        "subscriptions.csv",
    )


@router.get("/ai-usage.csv", summary="Export AI daily usage aggregates as CSV (superadmin)")
async def export_ai_usage(
    _admin: RequireSuperadmin,
    session: DbSession,
    since: str | None = Query(default=None, description="ISO 8601 lower bound for usage_date"),
    until: str | None = Query(default=None, description="ISO 8601 upper bound for usage_date"),
) -> StreamingResponse:
    stmt = (
        select(
            Bot.owner_id,
            User.email,
            Bot.id.label("bot_id"),
            Bot.name.label("bot_name"),
            DailyAIUsageAggregate.usage_date,
            DailyAIUsageAggregate.total_requests,
            DailyAIUsageAggregate.total_tokens,
            DailyAIUsageAggregate.total_cost_usd,
        )
        .join(Bot, DailyAIUsageAggregate.bot_id == Bot.id)
        .join(User, Bot.owner_id == User.id)
        .order_by(DailyAIUsageAggregate.usage_date.desc(), User.email)
        .limit(100_000)
    )
    dt_since = _parse_dt(since)
    dt_until = _parse_dt(until)
    if dt_since:
        stmt = stmt.where(DailyAIUsageAggregate.usage_date >= dt_since.date())
    if dt_until:
        stmt = stmt.where(DailyAIUsageAggregate.usage_date <= dt_until.date())
    rows = (await session.execute(stmt)).all()
    data = [
        [
            str(r.owner_id), r.email, str(r.bot_id), r.bot_name or "",
            str(r.usage_date),
            str(r.total_requests), str(r.total_tokens), str(r.total_cost_usd or 0),
        ]
        for r in rows
    ]
    return _csv_response(
        data,
        ["owner_id", "owner_email", "bot_id", "bot_name", "usage_date",
         "total_requests", "total_tokens", "total_cost_usd"],
        "ai_usage.csv",
    )


@router.get("/coupons.csv", summary="Export coupons as CSV (superadmin)")
async def export_coupons(
    _admin: RequireSuperadmin,
    session: DbSession,
    since: str | None = Query(default=None, description="ISO 8601 lower bound for created_at"),
    until: str | None = Query(default=None, description="ISO 8601 upper bound for created_at"),
) -> StreamingResponse:
    stmt = select(
        Coupon.id, Coupon.code, Coupon.discount_type, Coupon.discount_value,
        Coupon.target_plan, Coupon.max_uses, Coupon.used_count,
        Coupon.is_active, Coupon.expires_at, Coupon.created_at,
    ).order_by(Coupon.created_at)
    dt_since = _parse_dt(since)
    dt_until = _parse_dt(until)
    if dt_since:
        stmt = stmt.where(Coupon.created_at >= dt_since)
    if dt_until:
        stmt = stmt.where(Coupon.created_at <= dt_until)
    rows = (await session.execute(stmt)).all()
    data = [
        [
            str(r.id), r.code, r.discount_type, str(r.discount_value),
            r.target_plan or "", str(r.max_uses) if r.max_uses is not None else "",
            str(r.used_count), str(r.is_active),
            r.expires_at.isoformat() if r.expires_at else "",
            r.created_at.isoformat() if r.created_at else "",
        ]
        for r in rows
    ]
    return _csv_response(
        data,
        ["id", "code", "discount_type", "discount_value", "target_plan",
         "max_uses", "used_count", "is_active", "expires_at", "created_at"],
        "coupons.csv",
    )
