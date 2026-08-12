"""User identity and linked OAuth accounts."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    false,
    func,
    true,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import OAuthProvider, UserRole


class User(Base):
    """
    End-user identity.

    **Suspension:** ``is_active=False`` blocks login (existing). When a superadmin suspends an
    account, also set ``suspended_at`` and optionally ``suspension_reason`` for internal audit;
    :class:`~app.models.audit_log.AuditLog` rows should record the actor and metadata.
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index(
            "ix_users_created_at",
            "created_at",
            postgresql_ops={"created_at": "DESC NULLS LAST"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(
            UserRole,
            name="user_role",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=UserRole.customer_admin,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    lead_telegram_alerts_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
        comment="When true, new-lead routing may send Telegram owner alerts if a target is configured.",
    )
    lead_email_alerts_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
        comment="Reserved for future email lead alerts (currently unused).",
    )
    telegram_chat_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Telegram chat_id for per-customer lead alerts (set via linking flow).",
    )
    telegram_link_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="One-time code for Telegram deep-link pairing; cleared after linking.",
    )
    telegram_linked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the user linked their Telegram account.",
    )
    suspended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set when the account is suspended (typically with is_active=false); internal use.",
    )
    suspension_reason: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="Internal-only note for superadmin suspension (not shown on public APIs).",
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

    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        "OAuthAccount",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    bots: Mapped[list["Bot"]] = relationship(
        "Bot",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    leads: Mapped[list["Lead"]] = relationship(
        "Lead",
        back_populates="owner",
        foreign_keys="Lead.owner_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    knowledge_files: Mapped[list["KnowledgeFile"]] = relationship(
        "KnowledgeFile",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    knowledge_chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    widget_configs: Mapped[list["WidgetConfig"]] = relationship(
        "WidgetConfig",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    telegram_configs: Mapped[list["TelegramConfig"]] = relationship(
        "TelegramConfig",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    subscription: Mapped["Subscription | None"] = relationship(
        "Subscription",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[OAuthProvider] = mapped_column(
        SAEnum(
            OAuthProvider,
            name="oauth_provider",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[User] = relationship("User", back_populates="oauth_accounts")
