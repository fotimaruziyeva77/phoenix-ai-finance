"""Dashboard bell notifications for bot owners."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, false, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class OwnerNotification(Base):
    """
    Per-owner notification row for the dashboard bell icon.

    Created when a new lead is captured, bot status changes, or system events occur.
    ``is_read`` marks dismissal; unread count drives the badge number.
    """

    __tablename__ = "owner_notifications"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('new_lead', 'lead_update', 'bot_status', 'system')",
            name="ck_owner_notifications_kind_allowed",
        ),
        Index(
            "ix_owner_notifications_owner_unread",
            "owner_id",
            "is_read",
            postgresql_where="is_read = false",
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
    kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Notification type: new_lead, lead_update, bot_status, system.",
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Lead id, bot id, or other entity this notification refers to.",
    )
    reference_type: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="Entity type: lead, bot, etc.",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    owner = relationship("User")
