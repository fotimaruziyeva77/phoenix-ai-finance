"""Webhook delivery log (Stripe + Telegram)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Source: stripe | telegram
    source: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    # e.g. checkout.session.completed | invoice.payment_failed | telegram_update
    event_type: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    # received | processed | failed
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="received", index=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # First 2 KB of decoded payload — never store raw keys/tokens
    payload_preview: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # For telegram webhooks: which bot triggered it
    bot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()", index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
