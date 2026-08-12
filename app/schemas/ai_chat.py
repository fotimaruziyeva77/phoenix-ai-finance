"""API-facing shapes for AI chat orchestration."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ai_foundation import ConversationRead, MessageRead


class KnowledgeContextTurnMeta(BaseModel):
    """Per-turn knowledge RAG telemetry (optional; for dashboards and future usage logs)."""

    had_ready_knowledge_files: bool = Field(
        description="True if this bot had at least one knowledge file in ``ready`` state.",
    )
    retrieval_hit_count: int = Field(default=0, ge=0, description="Chunks matched before context budgeting.")
    context_chunk_count: int = Field(default=0, ge=0, description="Chunks included in the prompt after budgeting.")
    context_estimated_tokens: int = Field(
        default=0,
        ge=0,
        description="Sum of estimated tokens for selected context chunks.",
    )


class SendBotMessageResult(BaseModel):
    """Outcome of :meth:`~app.services.ai_service.AIService.send_bot_message`."""

    model_config = ConfigDict(from_attributes=True)

    conversation_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID | None = None
    assistant_text: str | None = None
    model_name: str | None = None
    success: bool
    error_code: str | None = None
    error_message: str | None = None
    error_category: str | None = Field(
        default=None,
        description="Normalized failure class; set for observability and API mapping.",
    )
    latency_ms: int | None = Field(default=None, ge=0)
    tokens_input: int | None = Field(default=None, ge=0)
    tokens_output: int | None = Field(default=None, ge=0)
    tokens_total: int | None = Field(default=None, ge=0)
    cost_usd: Decimal | None = None
    knowledge_context: KnowledgeContextTurnMeta | None = Field(
        default=None,
        description="Set when knowledge integration is wired; omit when disabled.",
    )


class BotDashboardChatTestRequest(BaseModel):
    """Body for dashboard bot test chat (creates conversation when ``conversation_id`` omitted)."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=32000,
        description="User message to send to the model (trimmed server-side).",
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Continue an existing test thread; omit to start a new conversation.",
    )


class BotDashboardChatTestResponse(BaseModel):
    """Successful dashboard test completion (HTTP 200)."""

    model_config = ConfigDict(from_attributes=True)

    conversation_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID = Field(description="Assistant turn persisted for this reply.")
    assistant_text: str
    model_name: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    tokens_input: int | None = Field(default=None, ge=0)
    tokens_output: int | None = Field(default=None, ge=0)
    tokens_total: int | None = Field(default=None, ge=0)
    cost_usd: Decimal | None = None
    knowledge_context: KnowledgeContextTurnMeta | None = Field(
        default=None,
        description="Echo of per-turn knowledge retrieval telemetry when integration is enabled.",
    )


class ConversationMessagesResponse(BaseModel):
    """Owner-scoped conversation with full transcript for dashboard testing."""

    conversation: ConversationRead
    messages: list[MessageRead]
