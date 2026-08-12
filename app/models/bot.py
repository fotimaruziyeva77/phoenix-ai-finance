"""Bot aggregate root for owner-scoped assistant configuration."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Bot(Base):
    """
    MVP bot profile, intentionally minimal and ready for config expansion.

    **Platform suspension:** ``platform_suspended_at`` (and optional ``platform_suspension_reason``)
    marks operator-enforced suspension. Product flows should treat a non-null timestamp as blocked
    (see :mod:`app.lib.platform_moderation`). Owner-driven pause remains ``status='paused'``.
    """

    __tablename__ = "bots"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','paused','archived','channel_pending')",
            name="ck_bots_status_allowed",
        ),
        CheckConstraint(
            "primary_channel IS NULL OR primary_channel IN ('web','telegram','both')",
            name="ck_bots_primary_channel_allowed",
        ),
        CheckConstraint(
            "goal_type IN ('support','sales','faq','consulting')",
            name="ck_bots_goal_type_allowed",
        ),
        Index(
            "ix_bots_updated_at",
            "updated_at",
            postgresql_ops={"updated_at": "DESC NULLS LAST"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    niche_id: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        comment="Config-driven niche key (non-enum for future catalog growth).",
    )
    goal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="draft",
        server_default="draft",
    )
    primary_channel: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="Wizard intent: web | telegram | both. Null for legacy rows.",
    )
    welcome_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    tone: Mapped[str | None] = mapped_column(String(120), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    short_description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    provider_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="gemini",
        server_default="gemini",
        comment="AI provider registry key (e.g. gemini, ollama).",
    )
    model_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Provider model id; null uses app default for this provider.",
    )
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
    platform_suspended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Superadmin/platform suspension timestamp; non-null means block public/runtime use.",
    )
    platform_suspension_reason: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="Internal-only reason for platform suspension.",
    )

    owner = relationship("User", back_populates="bots")
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="bot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="bot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    ai_usage_logs: Mapped[list["AIUsageLog"]] = relationship(
        "AIUsageLog",
        back_populates="bot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    daily_ai_usage_aggregates: Mapped[list["DailyAIUsageAggregate"]] = relationship(
        "DailyAIUsageAggregate",
        back_populates="bot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    leads: Mapped[list["Lead"]] = relationship(
        "Lead",
        back_populates="bot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    knowledge_files: Mapped[list["KnowledgeFile"]] = relationship(
        "KnowledgeFile",
        back_populates="bot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    knowledge_chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk",
        back_populates="bot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    widget_configs: Mapped[list["WidgetConfig"]] = relationship(
        "WidgetConfig",
        back_populates="bot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    telegram_config: Mapped["TelegramConfig | None"] = relationship(
        "TelegramConfig",
        back_populates="bot",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
