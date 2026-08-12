"""Read-only superadmin tenant diagnostics (aggregates + lists; audited, no impersonation)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.platform_admin_repository import PlatformAdminRepository, PlatformBotListFilters
from app.schemas.platform_admin import (
    AdminTenantAIUsageWindowSummary,
    AdminTenantChannelSummaryItem,
    AdminTenantDailyAIUsageRow,
    AdminTenantInspectionResponse,
    AdminTenantRecentAIFailure,
)
from app.services.audit_service import (
    TENANT_ACTION_SUPERADMIN_INSPECT,
    TENANT_ENTITY_TYPE,
    AuditService,
)
from app.services.platform_admin_service import PlatformAdminService

_WINDOW_DAYS = 7
_DAILY_ROLLUP_DAYS = 7
_BOT_PAGE_LIMIT = 200


class TenantInspectionService:
    def __init__(
        self,
        session: AsyncSession,
        repo: PlatformAdminRepository,
        audit: AuditService,
        views: PlatformAdminService,
    ) -> None:
        self._session = session
        self._repo = repo
        self._audit = audit
        self._views = views

    async def inspect_tenant(
        self,
        *,
        actor_user_id: uuid.UUID,
        owner_user_id: uuid.UUID,
    ) -> AdminTenantInspectionResponse | None:
        summary = await self._views.get_user(owner_user_id)
        if summary is None:
            return None

        now = datetime.now(UTC)
        since = now - timedelta(days=_WINDOW_DAYS)

        bots_page = await self._views.list_bots(
            filters=PlatformBotListFilters(owner_id=owner_user_id),
            limit=_BOT_PAGE_LIMIT,
            offset=0,
        )
        lead_count = await self._repo.count_leads_for_owner(owner_user_id)
        conversation_count = await self._repo.count_conversations_for_owner(owner_user_id)
        channel_rows = await self._repo.conversation_channel_breakdown_for_owner(owner_user_id)
        total_calls, ok_calls, fail_calls, total_tokens = await self._repo.ai_usage_stats_for_owner_since(
            owner_user_id,
            since,
        )
        daily_rows = await self._repo.daily_ai_usage_rollups_for_owner(
            owner_user_id,
            days=_DAILY_ROLLUP_DAYS,
        )
        failure_rows = await self._repo.recent_ai_failures_for_owner(owner_user_id, limit=15)

        await self._audit.log_entity_event(
            actor_user_id=actor_user_id,
            action=TENANT_ACTION_SUPERADMIN_INSPECT,
            entity_type=TENANT_ENTITY_TYPE,
            entity_id=owner_user_id,
            metadata_json={
                "inspection_version": 1,
                "window_days": _WINDOW_DAYS,
                "daily_rollup_days": _DAILY_ROLLUP_DAYS,
                "bot_rows_returned": len(bots_page.items),
                "bots_total_matching": bots_page.total,
                "lead_count": lead_count,
                "conversation_count": conversation_count,
                "channel_keys": sorted({c for c, _ in channel_rows}),
                "ai_calls_window": total_calls,
                "ai_success_window": ok_calls,
                "ai_failures_window": fail_calls,
                "recent_ai_failure_rows": len(failure_rows),
            },
        )
        await self._session.flush()

        return AdminTenantInspectionResponse(
            tenant_user_id=owner_user_id,
            summary=summary,
            bots=bots_page.items,
            channels=[AdminTenantChannelSummaryItem(channel=c, conversation_count=n) for c, n in channel_rows],
            lead_count=lead_count,
            conversation_count=conversation_count,
            ai_usage=AdminTenantAIUsageWindowSummary(
                period_start=since,
                period_end=now,
                total_calls=total_calls,
                successful_calls=ok_calls,
                failed_calls=fail_calls,
                total_tokens=total_tokens,
            ),
            ai_daily_usage=[
                AdminTenantDailyAIUsageRow(
                    usage_date=d,
                    total_requests=req,
                    total_tokens=tok,
                    total_cost_usd=float(cost),
                )
                for d, req, tok, cost in daily_rows
            ],
            recent_ai_failures=[
                AdminTenantRecentAIFailure(at=at, bot_id=bid, model_name=mn, error_code=ec)
                for at, bid, mn, ec in failure_rows
            ],
        )


__all__ = ["TenantInspectionService"]
