"""
Owner-scoped dashboard endpoints for testing bot chat.

* **Auth:** ``Authorization: Bearer <access_token>`` (same as other ``/api/v1`` routes).
* **AI:** Uses the configured provider (e.g. Gemini) via :class:`~app.services.ai_service.AIService`;
  there is no stubbed success path in production wiring.
* **Errors:** Failures raise :class:`~app.services.ai_exceptions.AIServiceHTTPError` subclasses → JSON
  ``StandardErrorResponse`` with ``category: "ai_chat"``, optional ``ai_category`` (timeout,
  auth_config, provider_unavailable, invalid_provider_response, internal_unknown), and
  ``details.retryable`` where applicable. No synthetic assistant rows: on provider failure the
  user message may already be persisted; the client should show the error and optionally refresh
  the transcript (see :mod:`app.services.ai_error_taxonomy`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import BillingServiceDep, BotChatTestServiceDep, CurrentUser, DbSession, SettingsDep
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.ai_usage_aggregate_repository import AIUsageAggregateRepository
from app.repositories.bot_repository import BotRepository
from app.schemas.ai_chat import (
    BotDashboardChatTestRequest,
    BotDashboardChatTestResponse,
    ConversationMessagesResponse,
)
from app.schemas.ai_quota import AIUsageQuotaRead
from app.services.ai_usage_quota_service import AIUsageQuotaService

router = APIRouter(tags=["bot-chat"])


@router.get(
    "/bots/{bot_id}/ai-usage-quota",
    response_model=AIUsageQuotaRead,
    summary="AI token usage vs configured caps (UTC windows)",
)
async def get_bot_ai_usage_quota(
    bot_id: UUID,
    user: CurrentUser,
    session: DbSession,
    settings: SettingsDep,
) -> AIUsageQuotaRead:
    bots = BotRepository(session)
    bot = await bots.get_bot_by_id(owner_id=user.id, bot_id=bot_id)
    if bot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
    repo = AIUsageAggregateRepository(session)
    svc = AIUsageQuotaService(repo, settings)
    return await svc.get_quota_read(bot_id=bot_id, owner_id=user.id)


@router.post(
    "/bots/{bot_id}/chat/test",
    response_model=BotDashboardChatTestResponse,
    summary="Send a test message to your bot (dashboard)",
)
async def post_bot_dashboard_chat_test(
    bot_id: UUID,
    payload: BotDashboardChatTestRequest,
    user: CurrentUser,
    session: DbSession,
    chat_test_service: BotChatTestServiceDep,
    billing_service: BillingServiceDep,
) -> BotDashboardChatTestResponse:
    # Enforce monthly conversation limit before processing
    now = datetime.now(UTC)
    chat_repo = AIChatRepository(session)
    monthly_count = await chat_repo.count_conversations_this_month_for_owner(
        user.id, year=now.year, month=now.month
    )
    await billing_service.enforce_conversation_limit(user, monthly_count)
    return await chat_test_service.send_dashboard_test_message(
        user=user,
        bot_id=bot_id,
        message=payload.message,
        conversation_id=payload.conversation_id,
    )


@router.get(
    "/bots/{bot_id}/conversations/{conversation_id}",
    response_model=ConversationMessagesResponse,
    summary="Get conversation transcript for dashboard testing",
)
async def get_bot_dashboard_conversation(
    bot_id: UUID,
    conversation_id: UUID,
    user: CurrentUser,
    chat_test_service: BotChatTestServiceDep,
) -> ConversationMessagesResponse:
    return await chat_test_service.get_conversation_for_dashboard(
        user=user,
        bot_id=bot_id,
        conversation_id=conversation_id,
    )
