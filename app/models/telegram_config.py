"""Telegram Bot API attachment for a BotForge bot (persistence only; no messaging here)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, false, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.telegram_channel_status import TELEGRAM_PROVISIONING_CHANNEL_PENDING
from app.models.base import Base


class TelegramConfig(Base):
    """
    One row per BotForge bot (optional channel).

    ``bot_token_encrypted`` holds a Fernet ciphertext encrypted with ``APP_TELEGRAM_TOKEN_FERNET_KEY``
    only (see ``app.lib.integration_secrets_crypto`` / ``app.lib.telegram_token_crypto``; independent of
    ``JWT_SECRET_KEY``). ``webhook_secret_token_encrypted`` uses the same Fernet key for
    Telegram's ``secret_token`` header verification — never store that in ``metadata_json``.
    ``is_connected`` reflects whether the webhook is registered and active (never True without a
    validated token and successful ``setWebhook``). ``provisioning_status`` drives owner UX
    (``channel_pending``, ``active``, ``failed_validation``). ``draft`` is API-only when no row exists.
    ``metadata_json`` is for non-secret Telegram metadata (e.g. ``telegram_bot_id`` from getMe).
    """

    __tablename__ = "telegram_configs"
    __table_args__ = (UniqueConstraint("bot_id", name="uq_telegram_configs_bot_id"),)

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
    bot_token_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Fernet ciphertext of the Telegram bot token; null while pending/failed validation.",
    )
    provisioning_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TELEGRAM_PROVISIONING_CHANNEL_PENDING,
        insert_default=TELEGRAM_PROVISIONING_CHANNEL_PENDING,
        comment="channel_pending | active | failed_validation (draft is API-only when no row).",
    )
    bot_username: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Telegram @username without @; filled after getMe or owner input.",
    )
    webhook_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        comment="Registered Telegram webhook HTTPS URL (refreshable).",
    )
    webhook_secret_token_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Fernet ciphertext of Telegram secret_token for inbound webhook verification.",
    )
    is_connected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
        comment="Lifecycle: False when paused, disconnected, or pending verification.",
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful getMe or webhook verification (UTC).",
    )
    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Extensible Telegram-side metadata (ids, webhook params); avoid secrets in plaintext.",
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

    bot: Mapped["Bot"] = relationship("Bot", back_populates="telegram_config")
    owner: Mapped["User"] = relationship("User", back_populates="telegram_configs")

    @property
    def has_stored_bot_token(self) -> bool:
        return bool((self.bot_token_encrypted or "").strip())
