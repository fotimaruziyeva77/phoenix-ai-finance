"""
Thin service for persisting :class:`~app.models.ai_foundation.AIUsageLog` rows.

Call sites (e.g. :class:`~app.services.ai_service.AIService`) should record every inference
attempt through this layer so logging rules stay centralized.
"""

from __future__ import annotations

from app.models.ai_foundation import AIUsageLog
from app.repositories.ai_chat_repository import AIChatRepository
from app.schemas.ai_usage import AIUsageLogPayload


class AIUsageLogService:
    """Writes usage logs via :class:`~app.repositories.ai_chat_repository.AIChatRepository`."""

    def __init__(self, chat_repo: AIChatRepository) -> None:
        self._chat = chat_repo

    async def record(self, payload: AIUsageLogPayload) -> AIUsageLog:
        return await self._chat.add_usage_log(
            bot_id=payload.bot_id,
            conversation_id=payload.conversation_id,
            message_id=payload.message_id,
            provider_name=payload.provider_name,
            model_name=payload.model_name,
            tokens_input=payload.tokens_input,
            tokens_output=payload.tokens_output,
            tokens_total=payload.tokens_total,
            latency_ms=payload.latency_ms,
            cost_usd=payload.cost_usd,
            success=payload.success,
            error_code=payload.error_code,
            step_kind=payload.step_kind,
        )
