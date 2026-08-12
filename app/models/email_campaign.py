"""Email campaign (admin-initiated bulk emails)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EmailCampaign(Base):
    __tablename__ = "email_campaigns"
    __table_args__ = (
        Index("ix_email_campaigns_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)

    # Segment: all_users | past_due | free_plan | paid_users | inactive_7d
    target_segment: Mapped[str] = mapped_column(String(32), nullable=False)

    # Status: draft | sending | sent | failed
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="draft")

    estimated_recipients: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
