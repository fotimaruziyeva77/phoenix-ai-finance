"""Embeddable website chat widget configuration (persistence only)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func, text, true
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.lib.public_widget_key import generate_public_widget_key
from app.models.base import Base


def new_public_widget_key() -> str:
    """Cryptographically strong, URL-safe public identifier (not sequential)."""
    return generate_public_widget_key()


class WidgetConfig(Base):
    """
    One row per embeddable widget instance.

    ``owner_id`` mirrors the bot owner for owner-scoped listing; keep it aligned with
    ``bot.owner_id`` on insert/update (same pattern as ``Lead``).
    """

    __tablename__ = "widget_configs"
    __table_args__ = (UniqueConstraint("public_widget_key", name="uq_widget_configs_public_widget_key"),)

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
    public_widget_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Opaque public token; generated in Python (secrets.token_urlsafe).",
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    allowed_domains_json: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        insert_default=list,
        server_default=text("'[]'::jsonb"),
        comment="Hostnames allowed to embed (e.g. example.com); enforced at runtime later.",
    )
    theme: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Optional preset theme key; richer theme JSON can live in widget_settings_json.",
    )
    welcome_text: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        comment="Widget-specific greeting; overrides bot default when set.",
    )
    pre_chat_form_json: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment='Pre-chat form fields, e.g. [{"name":"name","label":"Name","type":"text","required":true}].',
    )
    custom_css: Mapped[str | None] = mapped_column(
        String(8192),
        nullable=True,
        comment="Owner-provided CSS injected into the widget iframe (max 8 KB).",
    )
    widget_settings_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Reserved extension object: branding, layout/position, rate-limit hints, etc.",
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

    bot: Mapped["Bot"] = relationship("Bot", back_populates="widget_configs")
    owner: Mapped["User"] = relationship("User", back_populates="widget_configs")
