"""Support tickets — user-submitted help requests with admin reply."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

TICKET_STATUS_OPEN        = "open"
TICKET_STATUS_IN_PROGRESS = "in_progress"
TICKET_STATUS_RESOLVED    = "resolved"
TICKET_STATUS_CLOSED      = "closed"

TICKET_PRIORITY_LOW    = "low"
TICKET_PRIORITY_NORMAL = "normal"
TICKET_PRIORITY_HIGH   = "high"


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    __table_args__ = (
        Index("ix_support_tickets_user_id", "user_id"),
        Index("ix_support_tickets_status",  "status"),
        Index("ix_support_tickets_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[str]    = mapped_column(Text, nullable=False)
    status: Mapped[str]  = mapped_column(
        String(16), nullable=False, default=TICKET_STATUS_OPEN, server_default=TICKET_STATUS_OPEN
    )
    priority: Mapped[str] = mapped_column(
        String(8), nullable=False, default=TICKET_PRIORITY_NORMAL, server_default=TICKET_PRIORITY_NORMAL
    )
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
