"""
Public (unauthenticated) widget chat: same :class:`~app.services.ai_service.AIService` path as the dashboard.

Threads are ``web_widget`` rows from :class:`~app.services.web_widget_session_service.WebWidgetSessionService``.
Dashboard test chat uses ``admin_test``; Telegram uses its own adapter — all share one orchestrator and
``Conversation.channel`` for analytics and :attr:`~app.models.lead.Lead.source_channel``.
"""

from __future__ import annotations

from app.core.public_widget_abuse import widget_key_digest
from app.core.public_widget_channel_events import (
    WIDGET_MESSAGE_ANSWERED,
    WIDGET_MESSAGE_RECEIVED,
    emit_public_widget_channel_event,
    visitor_session_digest,
)
from app.lib.platform_moderation import bot_is_platform_suspended
from app.lib.widget_origin_policy import WidgetOriginPolicyOptions
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.bot_repository import BotRepository
from app.repositories.user_repository import UserRepository
from app.schemas.ai_chat import SendBotMessageResult
from app.schemas.public_widget_chat import PublicWidgetChatRequest, PublicWidgetChatResponse
from app.services.ai_error_taxonomy import (
    AI_CATEGORY_INVALID_PROVIDER_RESPONSE,
    exception_for_failed_send_result,
)
from app.services.ai_service import AIService
from app.services.billing_service import BillingService
from app.services.public_widget_chat_exceptions import (
    PublicWidgetChatBotSuspendedError,
    PublicWidgetChatConversationBindingError,
    PublicWidgetChatUnavailableError,
)
from app.services.web_widget_session_service import WebWidgetSessionService
from app.services.widget_bootstrap_exceptions import WidgetBootstrapNotFoundError
from app.services.widget_public_gate import (
    enforce_public_widget_origin_and_enabled,
    load_widget_and_bot_by_public_key,
)


class PublicWidgetChatService:
    def __init__(
        self,
        *,
        chat_repo: AIChatRepository,
        bot_repo: BotRepository,
        user_repo: UserRepository,
        ai_service: AIService,
        origin_policy: WidgetOriginPolicyOptions,
        billing_service: BillingService | None = None,
    ) -> None:
        self._chat = chat_repo
        self._users = user_repo
        self._ai = ai_service
        self._widget_sessions = WebWidgetSessionService(chat_repo, bot_repo)
        self._origin_policy = origin_policy
        self._billing = billing_service

    async def send_public_message(
        self,
        *,
        public_widget_key: str,
        origin_header: str | None,
        referer_header: str | None,
        body: PublicWidgetChatRequest,
    ) -> PublicWidgetChatResponse:
        ctx = await load_widget_and_bot_by_public_key(self._chat.session, public_widget_key)
        if ctx is None:
            raise WidgetBootstrapNotFoundError()
        wc, bot = ctx
        enforce_public_widget_origin_and_enabled(
            wc,
            origin_header=origin_header,
            referer_header=referer_header,
            origin_policy=self._origin_policy,
        )

        conv, visitor_key = await self._widget_sessions.get_or_create_conversation(
            bot_id=wc.bot_id,
            visitor_session_key=body.visitor_session_key,
        )
        if body.conversation_id is not None and body.conversation_id != conv.id:
            raise PublicWidgetChatConversationBindingError()

        digest = widget_key_digest(public_widget_key)
        vs_digest = visitor_session_digest(body.visitor_session_key)
        emit_public_widget_channel_event(
            event=WIDGET_MESSAGE_RECEIVED,
            bot_id=bot.id,
            widget_config_id=wc.id,
            widget_key_digest=digest,
            conversation_id=conv.id,
            visitor_session_digest=vs_digest,
            inbound_chars=len(body.message or ""),
        )

        owner = await self._users.get_by_id(bot.owner_id)
        if owner is None or not owner.is_active:
            raise PublicWidgetChatUnavailableError()
        if bot_is_platform_suspended(bot):
            raise PublicWidgetChatBotSuspendedError()

        # Enforce owner's monthly conversation limit (plan enforcement)
        if self._billing is not None:
            from datetime import UTC, datetime
            now = datetime.now(UTC)
            monthly_count = await self._chat.count_conversations_this_month_for_owner(
                owner.id, year=now.year, month=now.month
            )
            await self._billing.enforce_conversation_limit(owner, monthly_count)

        result = await self._ai.send_bot_message(
            bot,
            owner,
            body.message,
            conversation_id=conv.id,
        )
        self._raise_if_send_unusable(result)

        assert result.assistant_message_id is not None
        assert result.assistant_text is not None
        emit_public_widget_channel_event(
            event=WIDGET_MESSAGE_ANSWERED,
            bot_id=bot.id,
            widget_config_id=wc.id,
            widget_key_digest=digest,
            conversation_id=result.conversation_id,
            visitor_session_digest=vs_digest,
            latency_ms=result.latency_ms,
            inbound_chars=len(body.message or ""),
        )
        return PublicWidgetChatResponse(
            conversation_id=result.conversation_id,
            visitor_session_key=visitor_key,
            user_message_id=result.user_message_id,
            assistant_message_id=result.assistant_message_id,
            assistant_text=result.assistant_text,
            bot_display_name=bot.name,
        )

    def _raise_if_send_unusable(self, result: SendBotMessageResult) -> None:
        if not result.success:
            raise exception_for_failed_send_result(result)
        if not result.assistant_message_id or not result.assistant_text:
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
