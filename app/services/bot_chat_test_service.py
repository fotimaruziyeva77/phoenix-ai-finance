"""
**Channel adapter: dashboard test chat** — owner-scoped calls to :class:`~app.services.ai_service.AIService`.

New threads are tagged ``channel=admin_test`` (see ``AIService.send_bot_message``). Widget and Telegram
use their own adapters but the same orchestrator and lead pipeline keyed off ``Conversation.channel``.
"""

from __future__ import annotations

import uuid

from app.lib.platform_moderation import bot_is_platform_suspended
from app.models.user import User
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.bot_repository import BotRepository
from app.schemas.ai_chat import (
    BotDashboardChatTestResponse,
    ConversationMessagesResponse,
)
from app.schemas.ai_foundation import ConversationRead, MessageRead
from app.services.ai_error_taxonomy import (
    AI_CATEGORY_INVALID_PROVIDER_RESPONSE,
    exception_for_failed_send_result,
)
from app.services.ai_exceptions import (
    AIServiceBotPlatformSuspendedError,
    AIServiceForbiddenError,
    AIServiceNotFoundError,
)
from app.services.ai_service import AIService


class BotChatTestService:
    def __init__(
        self,
        *,
        bot_repo: BotRepository,
        chat_repo: AIChatRepository,
        ai_service: AIService,
    ) -> None:
        self._bots = bot_repo
        self._chat = chat_repo
        self._ai = ai_service

    async def send_dashboard_test_message(
        self,
        *,
        user: User,
        bot_id: uuid.UUID,
        message: str,
        conversation_id: uuid.UUID | None,
    ) -> BotDashboardChatTestResponse:
        # Owner gate (403 if missing). AIService re-loads the bot by owner for archived/status checks.
        bot = await self._bots.get_bot_by_id(owner_id=user.id, bot_id=bot_id)
        if bot is None:
            raise AIServiceForbiddenError()
        if bot_is_platform_suspended(bot):
            raise AIServiceBotPlatformSuspendedError()

        result = await self._ai.send_bot_message(
            bot,
            user,
            message,
            conversation_id=conversation_id,
        )
        if not result.success:
            raise exception_for_failed_send_result(result)
        if not result.assistant_message_id or not result.assistant_text:
            # Provider claimed success but nothing to show — treat as invalid/partial response (no fake assistant).
            raise exception_for_failed_send_result(
                result.model_copy(
                    update={
                        "success": False,
                        "error_code": result.error_code or "empty_completion",
                        "assistant_text": None,
                        "assistant_message_id": None,
                        "error_category": AI_CATEGORY_INVALID_PROVIDER_RESPONSE,
                    },
                ),
            )
        return BotDashboardChatTestResponse(
            conversation_id=result.conversation_id,
            user_message_id=result.user_message_id,
            assistant_message_id=result.assistant_message_id,
            assistant_text=result.assistant_text,
            model_name=result.model_name,
            latency_ms=result.latency_ms,
            tokens_input=result.tokens_input,
            tokens_output=result.tokens_output,
            tokens_total=result.tokens_total,
            cost_usd=result.cost_usd,
            knowledge_context=result.knowledge_context,
        )

    async def get_conversation_for_dashboard(
        self,
        *,
        user: User,
        bot_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> ConversationMessagesResponse:
        bot = await self._bots.get_bot_by_id(owner_id=user.id, bot_id=bot_id)
        if bot is None:
            raise AIServiceForbiddenError()

        conv = await self._chat.get_conversation_for_bot_owner(
            conversation_id=conversation_id,
            bot_id=bot_id,
            owner_id=user.id,
        )
        if conv is None:
            raise AIServiceNotFoundError()

        rows = await self._chat.list_messages_chronological(
            conversation_id=conversation_id,
            bot_id=bot_id,
        )
        return ConversationMessagesResponse(
            conversation=ConversationRead.model_validate(conv),
            messages=[MessageRead.model_validate(m) for m in rows],
        )
