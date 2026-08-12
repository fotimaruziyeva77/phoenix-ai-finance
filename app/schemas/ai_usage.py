"""DTOs for AI usage logging and daily rollups (no ORM)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

# Persisted on ``ai_usage_logs.step_kind`` for SQL rollups (conversation cost per step).
AI_USAGE_STEP_INTENT_CLASSIFIER = "intent_classifier"
AI_USAGE_STEP_LLM_CALL = "llm_call"
AI_USAGE_STEP_CHAT_COMPLETION = AI_USAGE_STEP_LLM_CALL
AI_USAGE_STEP_SEMANTIC_CACHE = "semantic_cache_hit"
AI_USAGE_STEP_EXACT_CACHE = "exact_cache_hit"
AI_USAGE_STEP_TRIVIAL = "trivial_handled"
AI_USAGE_STEP_SYNTHETIC_OUTPUT = "synthetic_output"
AI_USAGE_STEP_EMBEDDING_FAILED = "embedding_failed"


@dataclass(frozen=True, slots=True)
class AIUsageLogPayload:
    """Single inference call; maps 1:1 to :class:`~app.models.ai_foundation.AIUsageLog`."""

    bot_id: uuid.UUID
    conversation_id: uuid.UUID | None
    message_id: uuid.UUID | None
    provider_name: str
    model_name: str
    tokens_input: int
    tokens_output: int
    tokens_total: int
    latency_ms: int | None
    cost_usd: Decimal | None
    success: bool
    error_code: str | None
    step_kind: str | None = None


@dataclass(frozen=True, slots=True)
class DailyBotUsageRollup:
    """One row of analytics grouped by bot and calendar day (UTC)."""

    bot_id: uuid.UUID
    usage_date: date
    total_requests: int
    total_tokens: int
    total_cost_usd: Decimal
    avg_latency_ms: Decimal | None
