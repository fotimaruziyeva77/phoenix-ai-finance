"""Types for user-intent classification (separate from reply generation)."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Literal

from app.models.conversation_flow import ConversationDetectedIntent

IntentClassificationSource = Literal["rules", "gemini", "fallback", "sales_default", "trivial_fast_path"]


@dataclass(frozen=True, slots=True)
class IntentClassifierUsageContext:
    """When set, Gemini intent calls may write ``ai_usage_logs`` with ``step_kind=intent_classifier``."""

    bot_id: uuid.UUID
    conversation_id: uuid.UUID
    record_sales_llm_burst: Callable[[], Awaitable[None]] | None = field(default=None)


@dataclass(frozen=True, slots=True)
class IntentClassificationResult:
    """
    Normalized outcome of classifying a single user utterance.

    ``intent`` always matches :class:`~app.models.conversation_flow.ConversationDetectedIntent`
    values persisted on ``conversations.detected_intent``.
    """

    intent: ConversationDetectedIntent
    confidence: float
    source: IntentClassificationSource

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


def coerce_intent_label(raw: str | None) -> ConversationDetectedIntent | None:
    """Map arbitrary string to enum member, or None if not allowed."""
    if raw is None:
        return None
    key = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    if not key:
        return None
    try:
        return ConversationDetectedIntent(key)
    except ValueError:
        return None
