"""Coupon / promo codes — discount grants without Stripe."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

DISCOUNT_TYPE_PERCENT = "percent"   # e.g. 20 = 20% off
DISCOUNT_TYPE_USD     = "usd"       # e.g. 10 = $10 off


class Coupon(Base):
    """
    Promo / referral coupon.

    * ``discount_type=percent`` → ``discount_value`` is 0–100.
    * ``discount_type=usd``     → ``discount_value`` is a flat dollar amount.
    * ``target_plan`` NULL       → usable on any plan upgrade.
    * ``max_uses`` NULL          → unlimited.
    """

    __tablename__ = "coupons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, index=True,
        comment="Uppercase promo code, e.g. LAUNCH50."
    )
    discount_type: Mapped[str] = mapped_column(
        String(8), nullable=False, comment="percent | usd"
    )
    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="20 = 20% or $20 depending on discount_type."
    )
    target_plan: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="NULL = any plan; plan slug = only that tier."
    )
    max_uses: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="NULL = unlimited redemptions."
    )
    used_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
