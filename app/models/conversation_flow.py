"""
Stable sales-flow vocabulary for conversations (persistence + API validation).

Values are lowercase snake_case strings stored in PostgreSQL; extend enums here only with
new members and matching migrations (never rename in place — add aliases if needed).
"""

from __future__ import annotations

from enum import Enum


class ConversationFlowState(str, Enum):
    """High-level funnel position for structured multi-step AI sales flows."""

    start = "start"
    qualification = "qualification"
    clarification = "clarification"
    offer = "offer"
    objection_handling = "objection_handling"
    closing = "closing"
    fallback = "fallback"
    completed = "completed"


class ConversationDetectedIntent(str, Enum):
    """Last detected user intent; nullable when unknown or not yet classified."""

    greeting = "greeting"
    sales_interest = "sales_interest"
    support = "support"
    faq = "faq"
    consulting = "consulting"
    unknown = "unknown"


def _sql_in(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


_FLOW_STATE_VALUES: tuple[str, ...] = tuple(s.value for s in ConversationFlowState)
_INTENT_VALUES: tuple[str, ...] = tuple(s.value for s in ConversationDetectedIntent)

# For SQLAlchemy CheckConstraint text (keep in sync with migrations).
CHECK_CONVERSATION_FLOW_STATE = f"current_state IN ({_sql_in(_FLOW_STATE_VALUES)})"
CHECK_CONVERSATION_DETECTED_INTENT = (
    f"(detected_intent IS NULL OR detected_intent IN ({_sql_in(_INTENT_VALUES)}))"
)

__all__ = [
    "CHECK_CONVERSATION_DETECTED_INTENT",
    "CHECK_CONVERSATION_FLOW_STATE",
    "ConversationDetectedIntent",
    "ConversationFlowState",
]
