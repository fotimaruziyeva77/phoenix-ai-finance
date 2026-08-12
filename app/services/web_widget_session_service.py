"""
**Channel adapter: web widget** — resolve or create ``Conversation`` rows for the public embed.

Uses ``channel=web_widget`` and :class:`~app.repositories.ai_chat_repository.AIChatRepository`
(including :meth:`~app.repositories.ai_chat_repository.AIChatRepository.get_active_conversation_for_channel`
via :meth:`~app.repositories.ai_chat_repository.AIChatRepository.get_active_web_widget_conversation`).
Dashboard test chat uses ``admin_test``; Telegram uses :class:`~app.services.conversation_thread_service.ConversationThreadService`.
All share :class:`~app.services.ai_service.AIService` for turns (no second chat engine).
"""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.lib.chat_channels import CONVERSATION_CHANNEL_WEB_WIDGET
from app.lib.web_widget_visitor_session import (
    normalize_or_generate_visitor_session_key,
    sanitize_visitor_client_hint,
)
from app.models.ai_foundation import Conversation
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.bot_repository import BotRepository
from app.services.web_widget_session_exceptions import (
    WebWidgetSessionBotNotFoundError,
    WebWidgetSessionError,
    WebWidgetSessionValidationError,
)


class WebWidgetSessionService:
    """Get-or-create anonymous multi-turn threads keyed by opaque ``visitor_session_key``."""

    def __init__(self, chat_repo: AIChatRepository, bot_repo: BotRepository) -> None:
        self._chat = chat_repo
        self._bots = bot_repo

    async def get_or_create_conversation(
        self,
        *,
        bot_id: uuid.UUID,
        visitor_session_key: str | None,
        visitor_client_hint: str | None = None,
    ) -> tuple[Conversation, str]:
        """
        Return ``(conversation, visitor_session_key)``.

        The key is either validated from the client or newly generated; callers should return it
        to the browser so later requests can reconnect to the same thread.
        """
        bot = await self._bots.get_bot_by_id_unscoped(bot_id=bot_id)
        if bot is None:
            raise WebWidgetSessionBotNotFoundError()

        try:
            key = normalize_or_generate_visitor_session_key(visitor_session_key)
        except ValueError as exc:
            raise WebWidgetSessionValidationError(str(exc)) from exc

        hint = sanitize_visitor_client_hint(visitor_client_hint)

        existing = await self._chat.get_active_web_widget_conversation(
            bot_id=bot_id,
            public_visitor_session_key=key,
        )
        if existing is not None:
            return existing, key

        try:
            conv = await self._chat.create_conversation(
                bot_id=bot_id,
                owner_id=bot.owner_id,
                channel=CONVERSATION_CHANNEL_WEB_WIDGET,
                niche_id_snapshot=bot.niche_id,
                public_visitor_session_key=key,
                visitor_client_hint=hint,
            )
            return conv, key
        except IntegrityError:
            # Concurrent first message from the same visitor session raced on the partial unique
            # index. Recover by returning the winner's conversation instead of erroring (mirrors
            # the Telegram get-or-create path).
            await self._chat.session.rollback()
            retry = await self._chat.get_active_web_widget_conversation(
                bot_id=bot_id,
                public_visitor_session_key=key,
            )
            if retry is not None:
                return retry, key
            raise WebWidgetSessionError("Could not start web widget conversation")
        except SQLAlchemyError as exc:
            raise WebWidgetSessionError("Could not start web widget conversation") from exc
