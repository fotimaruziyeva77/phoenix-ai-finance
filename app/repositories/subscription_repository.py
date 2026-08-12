"""Repository for Subscription rows."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.enums import PlanSlug, SubscriptionStatus


class SubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> Subscription | None:
        result = await self._session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_stripe_customer_id(self, stripe_customer_id: str) -> Subscription | None:
        result = await self._session.execute(
            select(Subscription).where(
                Subscription.stripe_customer_id == stripe_customer_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_stripe_subscription_id(self, stripe_subscription_id: str) -> Subscription | None:
        result = await self._session.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_subscription_id
            )
        )
        return result.scalar_one_or_none()

    async def create_free(self, user_id: uuid.UUID) -> Subscription:
        """Provision a FREE subscription row for a new or existing user."""
        sub = Subscription(
            id=uuid.uuid4(),
            user_id=user_id,
            plan_slug=PlanSlug.free,
            status=SubscriptionStatus.active,
        )
        self._session.add(sub)
        return sub

    async def upsert_from_stripe(
        self,
        *,
        user_id: uuid.UUID,
        plan_slug: PlanSlug,
        status: SubscriptionStatus,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        stripe_price_id: str | None,
        current_period_start: datetime | None,
        current_period_end: datetime | None,
        canceled_at: datetime | None = None,
    ) -> Subscription:
        """Insert or update a subscription row from a Stripe webhook event."""
        sub = await self.get_by_user_id(user_id)
        if sub is None:
            sub = Subscription(id=uuid.uuid4(), user_id=user_id)
            self._session.add(sub)

        sub.plan_slug = plan_slug
        sub.status = status
        # Preserve existing Stripe ids when the incoming event omits them (e.g. async-payment
        # checkout, or events arriving out of order). Overwriting with "" would orphan the row
        # from Stripe so later `customer.subscription.*` events fail to resolve the user.
        if stripe_customer_id:
            sub.stripe_customer_id = stripe_customer_id
        if stripe_subscription_id:
            sub.stripe_subscription_id = stripe_subscription_id
        sub.stripe_price_id = stripe_price_id
        sub.current_period_start = current_period_start
        sub.current_period_end = current_period_end
        sub.canceled_at = canceled_at
        return sub

    async def set_stripe_customer(self, user_id: uuid.UUID, stripe_customer_id: str) -> None:
        await self._session.execute(
            update(Subscription)
            .where(Subscription.user_id == user_id)
            .values(stripe_customer_id=stripe_customer_id)
        )

    async def downgrade_to_free(self, user_id: uuid.UUID) -> Subscription | None:
        """Reset to FREE on subscription cancellation."""
        sub = await self.get_by_user_id(user_id)
        if sub:
            sub.plan_slug = PlanSlug.free
            sub.status = SubscriptionStatus.active
            sub.stripe_subscription_id = None
            sub.stripe_price_id = None
            sub.current_period_start = None
            sub.current_period_end = None
            sub.canceled_at = None
        return sub

    async def manual_override_plan(
        self,
        *,
        user_id: uuid.UUID,
        plan_slug: PlanSlug,
    ) -> Subscription | None:
        """
        Superadmin manual plan override: set the plan slug and keep status active.

        Intentionally preserves Stripe fields so billing webhooks can still
        reconcile later. Returns ``None`` if no subscription row exists for the user.
        """
        sub = await self.get_by_user_id(user_id)
        if sub is None:
            return None
        sub.plan_slug = plan_slug
        sub.status = SubscriptionStatus.active
        return sub

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
