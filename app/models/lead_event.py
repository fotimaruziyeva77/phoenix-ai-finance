"""Append-only CRM timeline rows for :class:`~app.models.lead.Lead`.

Rows must never be updated or deleted from application code; PostgreSQL triggers also block
mutations so support gets a tamper-evident audit trail.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class LeadEvent(Base):
    __tablename__ = "lead_events"

    EVENT_TYPES: ClassVar[frozenset[str]] = frozenset(
        {
            "lead_created",
            "lead_status_changed",
            "lead_assigned",
            "lead_reassigned",
            "note_added",
            "notification_delivered",
            "notification_failed",
            "lead_viewed",
            "system_action",
        }
    )
    ACTOR_TYPES: ClassVar[frozenset[str]] = frozenset({"user", "system", "integration"})

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    lead = relationship("Lead", back_populates="events")
