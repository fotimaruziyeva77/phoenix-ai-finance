"""Superadmin suspend/activate for users and bots (audited, reversible)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot import Bot
from app.models.user import User
from app.repositories.platform_admin_repository import PlatformAdminRepository
from app.schemas.platform_admin import AdminBotDetail, AdminUserDetail
from app.services.audit_service import (
    BOT_ACTION_PLATFORM_SUSPENDED,
    BOT_ACTION_PLATFORM_UNSUSPENDED,
    BOT_ENTITY_TYPE,
    USER_ACTION_SUSPENDED,
    USER_ACTION_UNSUSPENDED,
    USER_ENTITY_TYPE,
    AuditService,
    bot_audit_snapshot,
)
from app.services.platform_admin_service import PlatformAdminService


def _trim_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    s = reason.strip()
    return s or None


def _user_moderation_snapshot(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "suspended_at": user.suspended_at.isoformat() if user.suspended_at else None,
        "suspension_reason": user.suspension_reason,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def _bot_moderation_snapshot(bot: Bot) -> dict[str, Any]:
    return bot_audit_snapshot(
        {
            "id": bot.id,
            "owner_id": bot.owner_id,
            "name": bot.name,
            "niche_id": bot.niche_id,
            "goal_type": bot.goal_type,
            "status": bot.status,
            "welcome_message": bot.welcome_message,
            "tone": bot.tone,
            "language": bot.language,
            "short_description": bot.short_description,
            "provider_name": bot.provider_name,
            "model_name": bot.model_name,
            "temperature": bot.temperature,
            "max_output_tokens": bot.max_output_tokens,
            "updated_at": bot.updated_at,
            "platform_suspended_at": bot.platform_suspended_at,
            "platform_suspension_reason": bot.platform_suspension_reason,
        },
    )


class AdminModerationService:
    def __init__(
        self,
        session: AsyncSession,
        repo: PlatformAdminRepository,
        audit: AuditService,
        admin_views: PlatformAdminService,
    ) -> None:
        self._session = session
        self._repo = repo
        self._audit = audit
        self._views = admin_views

    async def suspend_user(
        self,
        *,
        actor_user_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str | None,
    ) -> AdminUserDetail | None:
        if user_id == actor_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot suspend your own account.",
            )
        user = await self._repo.get_user_with_oauth(user_id)
        if user is None:
            return None
        r = _trim_reason(reason)
        if user.suspended_at is not None and not user.is_active:
            detail = await self._views.get_user(user_id)
            assert detail is not None
            return detail

        before = _user_moderation_snapshot(user)
        now = datetime.now(UTC).replace(microsecond=0)
        user.is_active = False
        user.suspended_at = now
        user.suspension_reason = r
        after = _user_moderation_snapshot(user)
        await self._audit.log_entity_event(
            actor_user_id=actor_user_id,
            action=USER_ACTION_SUSPENDED,
            entity_type=USER_ENTITY_TYPE,
            entity_id=user.id,
            before_snapshot=before,
            after_snapshot=after,
            metadata_json={"reason": r} if r else None,
        )
        await self._session.flush()
        out = await self._views.get_user(user_id)
        assert out is not None
        return out

    async def activate_user(
        self,
        *,
        actor_user_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AdminUserDetail | None:
        user = await self._repo.get_user_with_oauth(user_id)
        if user is None:
            return None
        if user.is_active and user.suspended_at is None:
            detail = await self._views.get_user(user_id)
            assert detail is not None
            return detail

        before = _user_moderation_snapshot(user)
        user.is_active = True
        user.suspended_at = None
        user.suspension_reason = None
        after = _user_moderation_snapshot(user)
        await self._audit.log_entity_event(
            actor_user_id=actor_user_id,
            action=USER_ACTION_UNSUSPENDED,
            entity_type=USER_ENTITY_TYPE,
            entity_id=user.id,
            before_snapshot=before,
            after_snapshot=after,
        )
        await self._session.flush()
        out = await self._views.get_user(user_id)
        assert out is not None
        return out

    async def suspend_bot(
        self,
        *,
        actor_user_id: uuid.UUID,
        bot_id: uuid.UUID,
        reason: str | None,
    ) -> AdminBotDetail | None:
        bot = await self._repo.get_bot_unscoped(bot_id)
        if bot is None:
            return None
        r = _trim_reason(reason)
        if bot.platform_suspended_at is not None:
            detail = await self._views.get_bot(bot_id)
            assert detail is not None
            return detail

        before = _bot_moderation_snapshot(bot)
        now = datetime.now(UTC).replace(microsecond=0)
        bot.platform_suspended_at = now
        bot.platform_suspension_reason = r
        after = _bot_moderation_snapshot(bot)
        await self._audit.log_entity_event(
            actor_user_id=actor_user_id,
            action=BOT_ACTION_PLATFORM_SUSPENDED,
            entity_type=BOT_ENTITY_TYPE,
            entity_id=bot.id,
            before_snapshot=before,
            after_snapshot=after,
            metadata_json={"reason": r} if r else None,
        )
        await self._session.flush()
        out = await self._views.get_bot(bot_id)
        assert out is not None
        return out

    async def activate_bot(
        self,
        *,
        actor_user_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> AdminBotDetail | None:
        bot = await self._repo.get_bot_unscoped(bot_id)
        if bot is None:
            return None
        if bot.platform_suspended_at is None:
            detail = await self._views.get_bot(bot_id)
            assert detail is not None
            return detail

        before = _bot_moderation_snapshot(bot)
        bot.platform_suspended_at = None
        bot.platform_suspension_reason = None
        after = _bot_moderation_snapshot(bot)
        await self._audit.log_entity_event(
            actor_user_id=actor_user_id,
            action=BOT_ACTION_PLATFORM_UNSUSPENDED,
            entity_type=BOT_ENTITY_TYPE,
            entity_id=bot.id,
            before_snapshot=before,
            after_snapshot=after,
        )
        await self._session.flush()
        out = await self._views.get_bot(bot_id)
        assert out is not None
        return out
