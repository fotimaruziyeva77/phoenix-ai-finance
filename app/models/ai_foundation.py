"""AI messaging, usage, and cost accounting foundation (no inference logic)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.conversation_flow import (
    CHECK_CONVERSATION_DETECTED_INTENT,
    CHECK_CONVERSATION_FLOW_STATE,
    ConversationFlowState,
)


class Conversation(Base):
    """One chat thread for a bot; channel key reserved for web/Telegram etc."""

    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','closed')",
            name="ck_conversations_status_allowed",
        ),
        CheckConstraint(
            CHECK_CONVERSATION_FLOW_STATE,
            name="ck_conversations_current_state_allowed",
        ),
        CheckConstraint(
            CHECK_CONVERSATION_DETECTED_INTENT,
            name="ck_conversations_detected_intent_allowed",
        ),
        CheckConstraint(
            "(channel IS DISTINCT FROM 'web_widget') OR (public_visitor_session_key IS NOT NULL)",
            name="ck_conversations_web_widget_requires_visitor_key",
        ),
        CheckConstraint(
            "(channel IS DISTINCT FROM 'telegram') OR (telegram_chat_id IS NOT NULL)",
            name="ck_conversations_telegram_requires_chat_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="ingress: admin_test | web_widget | telegram | … — null for legacy rows.",
    )
    public_visitor_session_key: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Opaque anonymous visitor id for web_widget; required when channel is web_widget.",
    )
    telegram_chat_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Telegram chat id when channel is telegram; required for that channel.",
    )
    visitor_client_hint: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Optional non-PII client label for reconnect / coarse abuse bucketing.",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="active",
        server_default="active",
    )
    current_state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ConversationFlowState.start.value,
        server_default=ConversationFlowState.start.value,
        comment="Sales-flow position; driven by state machine (Sprint 7+), not raw model output.",
    )
    detected_intent: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="Last classified user intent; null until classifier runs or if unknown.",
    )
    niche_id_snapshot: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        index=True,
        comment="Bot niche_id at conversation start; preserves analytics if bot config changes.",
    )
    collected_data_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="Structured slots from qualification / lead capture (channel-agnostic JSON).",
    )
    last_user_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Last end-user turn timestamp; useful for follow-up jobs and SLA metrics.",
    )
    last_assistant_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last assistant turn timestamp.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    bot = relationship("Bot", back_populates="conversations")
    owner = relationship("User", back_populates="conversations")
    leads: Mapped[list["Lead"]] = relationship(
        "Lead",
        back_populates="conversation",
        passive_deletes=True,
        lazy="selectin",
    )
    messages: Mapped[list[Message]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Message.created_at",
    )


class Message(Base):
    """Single turn in a conversation; token/cost fields for accounting."""

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user','assistant','system')",
            name="ck_messages_role_allowed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 8), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    conversation = relationship("Conversation", back_populates="messages")
    bot = relationship("Bot", back_populates="messages")


class AIUsageLog(Base):
    """Immutable per-call usage row for auditing and reconciliation."""

    __tablename__ = "ai_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tokens_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 8), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    step_kind: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
        comment="intent_classifier, chat_completion, … — cost attribution per pipeline step.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    bot = relationship("Bot", back_populates="ai_usage_logs")


class DailyAIUsageAggregate(Base):
    """Rollup per bot per calendar day for dashboards and billing previews."""

    __tablename__ = "daily_ai_usage_aggregates"
    __table_args__ = (
        UniqueConstraint("bot_id", "usage_date", name="uq_daily_ai_usage_bot_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(16, 8),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )
    avg_latency_ms: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    bot = relationship("Bot", back_populates="daily_ai_usage_aggregates")
