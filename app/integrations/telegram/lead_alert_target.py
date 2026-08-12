"""
Resolve Telegram delivery target for a new lead.

MVP: optional **global** bot token + chat id from settings (dev / single-tenant).

Replace ``EnvLeadTelegramAlertTargetProvider`` with a DB-backed provider, e.g. columns on
``users`` or ``bots`` (``telegram_alert_chat_id``, ``telegram_bot_token_id`` → secrets vault),
without changing :class:`~app.services.telegram_lead_alert_service.TelegramLeadAlertService`.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.core.config import Settings
from app.integrations.telegram.lead_alert_types import TelegramSendTarget

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@runtime_checkable
class LeadTelegramAlertTargetProvider(Protocol):
    """Async resolver so DB or cache lookups stay non-blocking."""

    async def resolve_target(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> TelegramSendTarget | None: ...


class EnvLeadTelegramAlertTargetProvider:
    """
    Temporary single-target configuration via app settings.

    Ignores ``owner_id`` / ``bot_id`` until per-tenant storage exists; method signature stays stable.
    """

    def __init__(self, settings: Settings) -> None:
        token = (settings.telegram_lead_alert_bot_token or "").strip()
        chat = (settings.telegram_lead_alert_chat_id or "").strip()
        self._token = token
        self._chat = chat

    async def resolve_target(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> TelegramSendTarget | None:
        _ = owner_id, bot_id
        if not self._token or not self._chat:
            return None
        return TelegramSendTarget(bot_token=self._token, chat_id=self._chat)


class DbLeadTelegramAlertTargetProvider:
    """
    Per-customer Telegram target: platform bot token (env) + customer chat_id (DB).

    Falls back to global env chat_id when the owner has no linked Telegram.
    """

    def __init__(self, settings: Settings, session: "AsyncSession") -> None:
        self._token = (settings.telegram_lead_alert_bot_token or "").strip()
        self._fallback_chat = (settings.telegram_lead_alert_chat_id or "").strip()
        self._session = session

    async def resolve_target(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> TelegramSendTarget | None:
        _ = bot_id
        if not self._token:
            return None

        # Try per-customer chat_id from DB
        from sqlalchemy import select
        from app.models.user import User

        stmt = select(User.telegram_chat_id).where(User.id == owner_id)
        result = await self._session.execute(stmt)
        user_chat_id = result.scalar_one_or_none()

        chat_id = (user_chat_id or "").strip() or self._fallback_chat
        if not chat_id:
            return None
        return TelegramSendTarget(bot_token=self._token, chat_id=chat_id)
