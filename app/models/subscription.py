"""User subscription (one row per user; auto-provisioned as FREE on first access)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import PlanSlug, SubscriptionStatus


class Subscription(Base):
    """
    One row per user.  Created automatically as FREE when the user first hits
    a billing endpoint or creates a bot.

    Stripe fields are ``NULL`` for FREE / manually provisioned rows.
    ``current_period_end`` gates entitlement checks: treat NULL as perpetual
    for FREE, expired for paid tiers.
    """

    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_subscriptions_user_id"),
        Index("ix_subscriptions_stripe_customer_id", "stripe_customer_id"),
        Index("ix_subscriptions_stripe_subscription_id", "stripe_subscription_id"),
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
    plan_slug: Mapped[PlanSlug] = mapped_column(
        SAEnum(
            PlanSlug,
            name="plan_slug",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=PlanSlug.free,
        server_default=PlanSlug.free.value,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(
            SubscriptionStatus,
            name="subscription_status",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=SubscriptionStatus.active,
        server_default=SubscriptionStatus.active.value,
    )

    # Stripe integration fields (NULL for free-tier rows)
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Stripe Customer ID (cus_…); set on first checkout.",
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Stripe Subscription ID (sub_…).",
    )
    stripe_price_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Stripe Price ID (price_…) for the active plan.",
    )

    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Start of current billing period (from Stripe or manual).",
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="End of current billing period; NULL means perpetual (FREE).",
    )
    canceled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the subscription was canceled (access until period_end).",
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

    user: Mapped["User"] = relationship("User", back_populates="subscription", lazy="selectin")
