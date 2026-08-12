"""Pydantic shapes for AI conversations, messages, and usage (API-ready)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.conversation_flow import ConversationFlowState

ALLOWED_CONVERSATION_STATUS = ("active", "closed")
ALLOWED_MESSAGE_ROLE = ("user", "assistant", "system")


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bot_id: UUID
    owner_id: UUID
    channel: str | None
    status: str
    current_state: str = Field(
        default=ConversationFlowState.start.value,
        description="Sales-flow state machine position.",
    )
    detected_intent: str | None = Field(
        default=None,
        description="Last classified user intent, if any.",
    )
    niche_id_snapshot: str | None = Field(
        default=None,
        description="Bot niche_id when the conversation was started.",
    )
    collected_data_json: dict[str, object] = Field(
        default_factory=dict,
        description="Structured fields captured during the flow (e.g. qualification slots).",
    )
    last_user_message_at: datetime | None = None
    last_assistant_message_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    bot_id: UUID
    role: str
    content: str
    tokens_input: int | None
    tokens_output: int | None
    tokens_total: int | None
    latency_ms: int | None
    cost_usd: Decimal | None
    model_name: str | None
    created_at: datetime


class AIUsageLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bot_id: UUID
    conversation_id: UUID | None
    message_id: UUID | None
    provider_name: str
    model_name: str
    tokens_input: int = Field(..., ge=0)
    tokens_output: int = Field(..., ge=0)
    tokens_total: int = Field(..., ge=0)
    latency_ms: int | None
    cost_usd: Decimal | None
    success: bool
    error_code: str | None
    created_at: datetime


class DailyAIUsageAggregateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bot_id: UUID
    usage_date: date
    total_requests: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    total_cost_usd: Decimal
    avg_latency_ms: Decimal | None
