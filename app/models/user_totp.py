"""TOTP 2FA secret storage per user."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, false, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserTotp(Base):
    """
    One row per user who has configured TOTP 2FA.

    ``secret_encrypted`` stores the Fernet-encrypted TOTP base32 secret.
    ``recovery_codes_json`` stores hashed recovery codes (one-time use).
    ``is_active`` flips to true only after the user verifies the first code.
    """

    __tablename__ = "user_totp"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_totp_user_id"),)

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
    secret_encrypted: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Fernet-encrypted TOTP base32 secret.",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    recovery_codes_json: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Hashed recovery codes (argon2). Each entry: {hash, used}.",
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

    user: Mapped["User"] = relationship("User", backref="totp_config")
