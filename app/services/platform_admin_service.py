"""Superadmin platform overview (read-only lists and detail)."""

from __future__ import annotations

import uuid

from app.repositories.platform_admin_repository import (
    PlatformAdminRepository,
    PlatformBillingListFilters,
    PlatformBotListFilters,
    PlatformUserListFilters,
)
from datetime import UTC, datetime

from app.schemas.platform_admin import (
    AdminBillingListItem,
    AdminBillingListResponse,
    AdminBotDetail,
    AdminBotListItem,
    AdminBotListResponse,
    AdminOAuthProviderBrief,
    AdminPlatformStatsResponse,
    AdminSubscriptionDistributionItem,
    AdminUserDetail,
    AdminUserListItem,
    AdminUserListResponse,
)


class PlatformAdminService:
    def __init__(self, repo: PlatformAdminRepository) -> None:
        self._repo = repo

    @staticmethod
    def _has_password(user: object) -> bool:
        raw = getattr(user, "password_hash", None)
        return bool(raw and str(raw).strip())

    def _user_list_item(self, user: object, *, bot_count: int, oauth_count: int) -> AdminUserListItem:
        return AdminUserListItem(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            suspended_at=user.suspended_at,
            has_password=self._has_password(user),
            oauth_provider_count=oauth_count,
            bot_count=bot_count,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def list_users(
        self,
        *,
        filters: PlatformUserListFilters,
        limit: int,
        offset: int,
    ) -> AdminUserListResponse:
        total = await self._repo.count_users(filters)
        rows = await self._repo.list_users_with_counts(filters=filters, limit=limit, offset=offset)
        items = [self._user_list_item(u, bot_count=bc, oauth_count=oc) for u, bc, oc in rows]
        return AdminUserListResponse(items=items, total=total, limit=limit, offset=offset)

    async def get_user(self, user_id: uuid.UUID) -> AdminUserDetail | None:
        user = await self._repo.get_user_with_oauth(user_id)
        if user is None:
            return None
        accounts = list(user.oauth_accounts or [])
        oauth_count = len(accounts)
        bot_count = await self._repo.count_bots_for_owner(user.id)
        base = self._user_list_item(user, bot_count=bot_count, oauth_count=oauth_count)
        return AdminUserDetail(
            **base.model_dump(),
            suspension_reason=user.suspension_reason,
            oauth_providers=[AdminOAuthProviderBrief(provider=a.provider) for a in accounts],
        )

    async def list_bots(
        self,
        *,
        filters: PlatformBotListFilters,
        limit: int,
        offset: int,
    ) -> AdminBotListResponse:
        total = await self._repo.count_bots(filters)
        rows = await self._repo.list_bots_with_overview(filters=filters, limit=limit, offset=offset)
        items = [
            AdminBotListItem(
                id=b.id,
                owner_id=b.owner_id,
                owner_email=email,
                name=b.name,
                niche_id=b.niche_id,
                goal_type=b.goal_type,
                status=b.status,
                provider_name=b.provider_name,
                model_name=b.model_name,
                widget_configured=hw,
                telegram_connected=ht,
                platform_suspended_at=b.platform_suspended_at,
                created_at=b.created_at,
                updated_at=b.updated_at,
            )
            for b, email, hw, ht in rows
        ]
        return AdminBotListResponse(items=items, total=total, limit=limit, offset=offset)

    async def get_bot(self, bot_id: uuid.UUID) -> AdminBotDetail | None:
        bot = await self._repo.get_bot_unscoped(bot_id)
        if bot is None:
            return None
        owner_email = await self._repo.get_owner_email(bot.owner_id)
        if owner_email is None:
            owner_email = ""
        hw = (await self._repo.widget_row_count_for_bot(bot.id)) > 0
        ht = await self._repo.telegram_connected_for_bot(bot.id)
        base = AdminBotListItem(
            id=bot.id,
            owner_id=bot.owner_id,
            owner_email=owner_email,
            name=bot.name,
            niche_id=bot.niche_id,
            goal_type=bot.goal_type,
            status=bot.status,
            provider_name=bot.provider_name,
            model_name=bot.model_name,
            widget_configured=hw,
            telegram_connected=ht,
            platform_suspended_at=bot.platform_suspended_at,
            created_at=bot.created_at,
            updated_at=bot.updated_at,
        )
        return AdminBotDetail(
            **base.model_dump(),
            platform_suspension_reason=bot.platform_suspension_reason,
            welcome_message=bot.welcome_message,
            tone=bot.tone,
            language=bot.language,
            short_description=bot.short_description,
            temperature=bot.temperature,
            max_output_tokens=bot.max_output_tokens,
        )


    async def list_billing(
        self,
        *,
        filters: PlatformBillingListFilters,
        limit: int,
        offset: int,
    ) -> AdminBillingListResponse:
        total = await self._repo.count_billing(filters)
        rows = await self._repo.list_billing(filters=filters, limit=limit, offset=offset)
        items = [
            AdminBillingListItem(
                user_id=sub.user_id,
                user_email=email,
                user_full_name=full_name,
                user_is_active=is_active,
                plan_slug=sub.plan_slug.value if hasattr(sub.plan_slug, "value") else str(sub.plan_slug),
                status=sub.status.value if hasattr(sub.status, "value") else str(sub.status),
                stripe_customer_id=sub.stripe_customer_id,
                stripe_subscription_id=sub.stripe_subscription_id,
                current_period_start=sub.current_period_start,
                current_period_end=sub.current_period_end,
                canceled_at=sub.canceled_at,
                created_at=sub.created_at,
                updated_at=sub.updated_at,
            )
            for sub, email, full_name, is_active in rows
        ]
        return AdminBillingListResponse(items=items, total=total, limit=limit, offset=offset)

    async def get_platform_stats(self) -> AdminPlatformStatsResponse:
        raw = await self._repo.get_platform_stats()
        billing = await self._repo.get_billing_stats()
        dist = [
            AdminSubscriptionDistributionItem(plan_slug=slug, count=count)
            for slug, count in raw["subscription_distribution"]
        ]
        return AdminPlatformStatsResponse(
            total_users=raw["total_users"],
            active_users=raw["active_users"],
            total_bots=raw["total_bots"],
            active_bots=raw["active_bots"],
            total_leads=raw["total_leads"],
            total_conversations=raw["total_conversations"],
            subscription_distribution=dist,
            mrr_usd=billing["mrr_usd"],
            total_paid_active=billing["total_paid_active"],
            total_free=billing["total_free"],
            total_past_due=billing["total_past_due"],
            total_canceled=billing["total_canceled"],
            generated_at=datetime.now(UTC),
        )


__all__ = ["PlatformAdminService"]
