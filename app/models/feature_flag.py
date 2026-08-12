"""Feature flags — runtime toggles for plan-level or global feature rollouts."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FeatureFlag(Base):
    """
    One row per feature key.  Admin can toggle flags on/off without deploying.

    * ``target_plan`` NULL  → flag applies globally (all plans).
    * ``target_plan`` set   → flag only affects users on that plan slug.
    """

    __tablename__ = "feature_flags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="Machine-readable identifier, e.g. 'advanced_analytics', 'api_access'.",
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    target_plan: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="NULL = all plans; set to a plan slug to scope the flag to that tier.",
    )
    target_user_ids: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of user UUIDs to target. NULL = no user-level targeting.",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Human-readable note for admin UI."
    )
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
