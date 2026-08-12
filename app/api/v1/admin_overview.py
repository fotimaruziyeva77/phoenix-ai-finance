"""Superadmin platform overview (users / bots / billing / audit log / AI usage)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import (
    AdminModerationServiceDep,
    AuditLogRepoDep,
    DbSession,
    PlatformAdminRepoDep,
    PlatformAdminServiceDep,
    RequireSuperadmin,
    SubscriptionRepoDep,
)
from app.models.enums import PlanSlug, UserRole
from app.repositories.audit_log_repository import AuditLogFilters
from app.repositories.platform_admin_repository import (
    PlatformBillingListFilters,
    PlatformBotListFilters,
    PlatformUserListFilters,
)
from app.schemas.platform_admin import (
    AdminAIUsageDailyRow,
    AdminAIUsagePlatformStats,
    AdminAIUsageResponse,
    AdminAIUsageTopConsumer,
    AdminAuditLogItem,
    AdminAuditLogListResponse,
    AdminAuditLogMetaResponse,
    AdminBillingListResponse,
    AdminBotDetail,
    AdminBotListResponse,
    AdminPlatformStatsResponse,
    AdminSubscriptionOverrideBody,
    AdminSubscriptionRead,
    AdminUserDetail,
    AdminUserListResponse,
)

router = APIRouter(prefix="/admin", tags=["admin-overview"])

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


@router.get(
    "/stats",
    response_model=AdminPlatformStatsResponse,
    summary="Platform-wide aggregate stats (superadmin)",
)
async def admin_platform_stats(
    _admin: RequireSuperadmin,
    svc: PlatformAdminServiceDep,
) -> AdminPlatformStatsResponse:
    return await svc.get_platform_stats()


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List platform users (superadmin)",
)
async def admin_list_users(
    _admin: RequireSuperadmin,
    svc: PlatformAdminServiceDep,
    role: UserRole | None = Query(default=None, description="Filter by application role."),
    is_active: bool | None = Query(default=None, description="Filter by active flag."),
    search: str | None = Query(default=None, description="Search by email or name (case-insensitive)."),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> AdminUserListResponse:
    filters = PlatformUserListFilters(role=role, is_active=is_active, search=search)
    return await svc.list_users(filters=filters, limit=limit, offset=offset)


@router.get(
    "/users/{user_id}",
    response_model=AdminUserDetail,
    summary="Get one user (superadmin)",
)
async def admin_get_user(
    user_id: UUID,
    _admin: RequireSuperadmin,
    svc: PlatformAdminServiceDep,
) -> AdminUserDetail:
    row = await svc.get_user(user_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return row


@router.get(
    "/bots",
    response_model=AdminBotListResponse,
    summary="List all bots (superadmin)",
)
async def admin_list_bots(
    _admin: RequireSuperadmin,
    svc: PlatformAdminServiceDep,
    owner_id: UUID | None = Query(default=None),
    niche_id: str | None = Query(default=None, description="Exact niche_id match."),
    status: str | None = Query(default=None, description="Bot status (draft, active, paused, archived)."),
    has_widget: bool | None = Query(default=None, description="Widget config row exists."),
    has_telegram_connected: bool | None = Query(
        default=None,
        description="Telegram row exists with is_connected=true.",
    ),
    platform_suspended: bool | None = Query(
        default=None,
        description="True: platform_suspended_at set; False: not set.",
    ),
    search: str | None = Query(default=None, description="Search by bot name or owner email (case-insensitive)."),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> AdminBotListResponse:
    filters = PlatformBotListFilters(
        owner_id=owner_id,
        niche_id=niche_id,
        status=status,
        has_widget=has_widget,
        has_telegram_connected=has_telegram_connected,
        platform_suspended=platform_suspended,
        search=search,
    )
    return await svc.list_bots(filters=filters, limit=limit, offset=offset)


@router.get(
    "/bots/{bot_id}",
    response_model=AdminBotDetail,
    summary="Get one bot (superadmin)",
)
async def admin_get_bot(
    bot_id: UUID,
    _admin: RequireSuperadmin,
    svc: PlatformAdminServiceDep,
) -> AdminBotDetail:
    row = await svc.get_bot(bot_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found.")
    return row


@router.post(
    "/users/{user_id}/subscription/override",
    response_model=AdminSubscriptionRead,
    summary="Manually override a user's subscription plan (superadmin)",
)
async def admin_override_subscription(
    user_id: UUID,
    body: AdminSubscriptionOverrideBody,
    _admin: RequireSuperadmin,
    sub_repo: SubscriptionRepoDep,
) -> AdminSubscriptionRead:
    """Force-set a user's plan without Stripe. Useful for trials, comps, or billing fixes."""
    try:
        plan = PlanSlug(body.plan_slug)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown plan slug: {body.plan_slug!r}",
        )
    sub = await sub_repo.manual_override_plan(user_id=user_id, plan_slug=plan)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found for this user.")
    _user_id = sub.user_id
    await sub_repo.commit()
    refreshed = await sub_repo.get_by_user_id(_user_id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Subscription disappeared after update.")
    return AdminSubscriptionRead(
        user_id=refreshed.user_id,
        plan_slug=refreshed.plan_slug.value,
        status=refreshed.status.value,
        updated_at=refreshed.updated_at,
    )


@router.get(
    "/billing/subscriptions",
    response_model=AdminBillingListResponse,
    summary="List all subscriptions with user info (superadmin billing)",
)
async def admin_list_billing(
    _admin: RequireSuperadmin,
    svc: PlatformAdminServiceDep,
    status_filter: str | None = Query(default=None, alias="status"),
    plan_slug: str | None = Query(default=None),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> AdminBillingListResponse:
    filters = PlatformBillingListFilters(status=status_filter, plan_slug=plan_slug)
    return await svc.list_billing(filters=filters, limit=limit, offset=offset)


# ── Audit Log ───────────────────────────────────────────────────────────────

@router.get(
    "/audit-logs",
    response_model=AdminAuditLogListResponse,
    summary="List admin audit log events (superadmin)",
)
async def admin_list_audit_logs(
    _admin: RequireSuperadmin,
    audit_repo: AuditLogRepoDep,
    actor_user_id: UUID | None = Query(default=None, description="Filter by the admin who performed the action."),
    entity_type: str | None = Query(default=None, description="Filter by entity type: user, bot, tenant, subscription…"),
    entity_id: UUID | None = Query(default=None, description="Filter by a specific entity UUID."),
    action: str | None = Query(default=None, description="Filter by action string, e.g. 'user_suspended'."),
    since: str | None = Query(default=None, description="ISO 8601 datetime lower bound."),
    until: str | None = Query(default=None, description="ISO 8601 datetime upper bound."),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> AdminAuditLogListResponse:
    """
    Paginated audit trail of all superadmin actions on the platform.
    Filter by actor, entity type, entity id, or action string.
    """
    from datetime import datetime

    def _parse_dt(s: str | None):
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid datetime format: {s!r}. Use ISO 8601.",
            )

    filters = AuditLogFilters(
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        since=_parse_dt(since),
        until=_parse_dt(until),
    )
    total = await audit_repo.count(filters)
    rows = await audit_repo.list(filters, limit=limit, offset=offset)
    items = [
        AdminAuditLogItem(
            id=log.id,
            actor_user_id=log.actor_user_id,
            actor_email=email,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            before_snapshot=log.before_snapshot,
            after_snapshot=log.after_snapshot,
            metadata_json=log.metadata_json,
            created_at=log.created_at,
        )
        for log, email in rows
    ]
    return AdminAuditLogListResponse(
        items=items, total=total, limit=limit, offset=offset
    )


@router.get(
    "/audit-logs/meta",
    response_model=AdminAuditLogMetaResponse,
    summary="Distinct action and entity_type values for filter dropdowns",
)
async def admin_audit_log_meta(
    _admin: RequireSuperadmin,
    audit_repo: AuditLogRepoDep,
) -> AdminAuditLogMetaResponse:
    actions = await audit_repo.distinct_actions()
    entity_types = await audit_repo.distinct_entity_types()
    return AdminAuditLogMetaResponse(actions=actions, entity_types=entity_types)


# ── AI Usage Monitor ────────────────────────────────────────────────────────

@router.get(
    "/ai-usage",
    response_model=AdminAIUsageResponse,
    summary="Platform-wide AI usage monitor (superadmin)",
)
async def admin_ai_usage(
    _admin: RequireSuperadmin,
    repo: PlatformAdminRepoDep,
    days: int = Query(default=30, ge=1, le=90, description="Look-back window in days (1–90)."),
    top: int = Query(default=10, ge=1, le=50, description="Number of top consumers to return."),
) -> AdminAIUsageResponse:
    """
    Returns platform-wide AI call totals, daily breakdown, and top token consumers.
    Use days=7 for weekly view, days=30 for monthly, days=90 for quarterly.
    """
    stats_raw, daily_raw, consumers_raw = await _gather_ai_usage(repo, days=days, top=top)

    stats = AdminAIUsagePlatformStats(**stats_raw)
    daily = [
        AdminAIUsageDailyRow(
            usage_date=r[0],
            total_requests=r[1],
            total_tokens=r[2],
            total_cost_usd=float(r[3]),
        )
        for r in daily_raw
    ]
    top_consumers = [
        AdminAIUsageTopConsumer(
            owner_id=r[0],
            owner_email=r[1],
            total_tokens=r[2],
            total_cost_usd=float(r[3]),
            total_calls=r[4],
        )
        for r in consumers_raw
    ]
    return AdminAIUsageResponse(stats=stats, daily=daily, top_consumers=top_consumers)


async def _gather_ai_usage(repo, *, days: int, top: int):
    import asyncio
    return await asyncio.gather(
        repo.platform_ai_usage_stats(days=days),
        repo.platform_daily_ai_usage(days=days),
        repo.top_ai_consumers(days=days, limit=top),
    )


# ── Bulk Bot Actions ──────────────────────────────────────────────────────


class BulkBotActionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(..., pattern="^(suspend|activate)$")
    bot_ids: list[UUID] = Field(..., min_length=1, max_length=100)
    reason: str | None = Field(default=None, max_length=500)


class BulkBotActionResult(BaseModel):
    bot_id: UUID
    success: bool
    error: str | None = None


class BulkBotActionResponse(BaseModel):
    results: list[BulkBotActionResult]
    succeeded: int
    failed: int


@router.post(
    "/bots/bulk-action",
    response_model=BulkBotActionResponse,
    summary="Bulk suspend/activate bots (superadmin)",
)
async def admin_bulk_bot_action(
    body: BulkBotActionBody,
    admin: RequireSuperadmin,
    svc: AdminModerationServiceDep,
    session: DbSession,
) -> BulkBotActionResponse:
    results: list[BulkBotActionResult] = []

    for bot_id in body.bot_ids:
        try:
            if body.action == "suspend":
                result = await svc.suspend_bot(
                    actor_user_id=admin.id,
                    bot_id=bot_id,
                    reason=body.reason,
                )
                if result is None:
                    results.append(BulkBotActionResult(bot_id=bot_id, success=False, error="Bot not found."))
                else:
                    results.append(BulkBotActionResult(bot_id=bot_id, success=True))

            elif body.action == "activate":
                result = await svc.activate_bot(
                    actor_user_id=admin.id,
                    bot_id=bot_id,
                )
                if result is None:
                    results.append(BulkBotActionResult(bot_id=bot_id, success=False, error="Bot not found."))
                else:
                    results.append(BulkBotActionResult(bot_id=bot_id, success=True))

        except HTTPException as exc:
            results.append(BulkBotActionResult(bot_id=bot_id, success=False, error=exc.detail))
        except Exception as exc:  # noqa: BLE001
            results.append(BulkBotActionResult(bot_id=bot_id, success=False, error=str(exc)))

    await session.commit()

    succeeded = sum(1 for r in results if r.success)
    failed = len(results) - succeeded
    return BulkBotActionResponse(results=results, succeeded=succeeded, failed=failed)
