"""
Shared **conversation thread** resolution for channels that are not the dashboard test chat.

**Widget threads** stay in :class:`~app.services.web_widget_session_service.WebWidgetSessionService`
(visitor key normalization + abuse hints). This module holds **Telegram** (and future keyed channels)
so :class:`~app.services.telegram_webhook_inbound_service.TelegramWebhookInboundService` stays a
thin transport adapter around ``AIService`` + outbound reply.

All paths use :class:`~app.repositories.ai_chat_repository.AIChatRepository` and the same
``Conversation`` / sales-orchestrator core as the widget.
"""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError

from app.lib.chat_channels import CONVERSATION_CHANNEL_TELEGRAM
from app.models.ai_foundation import Conversation
from app.repositories.ai_chat_repository import AIChatRepository


class ConversationThreadService:
    """Get-or-create active ``Conversation`` rows keyed by channel-specific external ids."""

    def __init__(self, chat_repo: AIChatRepository) -> None:
        self._chat = chat_repo

    async def get_or_create_telegram_thread(
        self,
        *,
        bot_id: uuid.UUID,
        owner_id: uuid.UUID,
        niche_id_snapshot: str | None,
        telegram_chat_id: int,
    ) -> Conversation:
        existing = await self._chat.get_active_telegram_conversation(
            bot_id=bot_id,
            telegram_chat_id=telegram_chat_id,
        )
        if existing is not None:
            return existing
        try:
            return await self._chat.create_conversation(
                bot_id=bot_id,
                owner_id=owner_id,
                channel=CONVERSATION_CHANNEL_TELEGRAM,
                niche_id_snapshot=niche_id_snapshot,
                telegram_chat_id=telegram_chat_id,
            )
        except IntegrityError:
            await self._chat.session.rollback()
            retry = await self._chat.get_active_telegram_conversation(
                bot_id=bot_id,
                telegram_chat_id=telegram_chat_id,
            )
            if retry is not None:
                return retry
            raise
