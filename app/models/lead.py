"""
Owner-scoped captured lead rows for CRM pipeline (persistence only; no sync logic).

**Timeline:** Append-only rows live in :class:`~app.models.lead_event.LeadEvent` (``lead_events``),
queried for support and CRM activity feeds.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

_CHECK_LEAD_STATUS = (
    "status IN ('new','contacted','qualified','proposal','won','lost')"
)
_CHECK_LEAD_TEMPERATURE = (
    "lead_temperature IS NULL OR lead_temperature IN ('cold','warm','hot')"
)
_CHECK_TELEGRAM_DELIVERY = (
    "telegram_delivery_status IS NULL OR telegram_delivery_status IN ("
    "'skipped_not_configured', 'skipped_no_target', 'skipped_owner_pref', "
    "'delivered', 'failed')"
)

# Open pipeline stages for creation-time duplicate-phone checks (see ``lead_safeguards``).
LEAD_OPEN_PIPELINE_STATUSES: tuple[str, ...] = (
    "new",
    "contacted",
    "qualified",
    "proposal",
)


class Lead(Base):
    """
    One pipeline row per captured opportunity.

    ``owner_id`` mirrors the bot owner for cheap owner-scoped listing without always joining ``bots``.
    Callers should keep ``owner_id`` consistent with ``bot.owner_id`` when inserting/updating.
    """

    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint(_CHECK_LEAD_STATUS, name="ck_leads_status_allowed"),
        CheckConstraint(_CHECK_LEAD_TEMPERATURE, name="ck_leads_temperature_allowed"),
        CheckConstraint(
            "lead_score IS NULL OR (lead_score >= 0 AND lead_score <= 100)",
            name="ck_leads_score_range",
        ),
        CheckConstraint(_CHECK_TELEGRAM_DELIVERY, name="ck_leads_telegram_delivery_status_allowed"),
        Index(
            "uq_leads_conversation_id_not_null",
            "conversation_id",
            unique=True,
            postgresql_where=text("conversation_id IS NOT NULL"),
        ),
        Index(
            "ix_leads_owner_id_updated_at",
            "owner_id",
            "updated_at",
            postgresql_ops={"updated_at": "DESC NULLS LAST"},
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
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    niche_id: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
        comment="Niche key at capture time (aligned with bot/niche registry).",
    )
    lead_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Optional score 0–100; null when not computed.",
    )
    lead_temperature: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="cold | warm | hot; null when unknown.",
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="new",
        server_default="new",
        index=True,
    )
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Owner-editable CRM notes; distinct from AI-generated summary.",
    )
    assignee_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional workspace assignee (FK to users); owner may delegate from the dashboard.",
    )
    source_channel: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Copied from Conversation.channel at capture (admin_test, web_widget, telegram, …).",
    )
    collected_data_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Snapshot of structured fields at capture; optional if only name/phone stored.",
    )
    owner_inbox_routed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When set, lead is confirmed visible to the owner CRM inbox (dashboard API).",
    )
    telegram_delivery_status: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment=(
            "skipped_not_configured | skipped_no_target | skipped_owner_pref | delivered | failed"
        ),
    )
    telegram_delivery_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Telegram Bot API attempts for the last new-lead alert (includes retries).",
    )
    telegram_delivery_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time telegram_delivery_status changed.",
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

    bot = relationship("Bot", back_populates="leads")
    owner = relationship("User", back_populates="leads", foreign_keys="Lead.owner_id")
    assignee = relationship("User", foreign_keys="Lead.assignee_user_id", viewonly=True)
    conversation = relationship("Conversation", back_populates="leads")
    events = relationship(
        "LeadEvent",
        back_populates="lead",
        order_by="LeadEvent.created_at",
        passive_deletes=True,
    )
