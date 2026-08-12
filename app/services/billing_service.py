"""Billing service — subscription management, plan enforcement, Stripe integration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.enums import PlanSlug, SubscriptionStatus
from app.models.subscription import Subscription
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.services.billing_exceptions import (
    AlreadyOnPlanError,
    AnalyticsNotAllowedError,
    BotLimitExceededError,
    ChannelNotAllowedError,
    ConversationLimitExceededError,
    PdfLimitExceededError,
    PlanNotFoundError,
    StorageLimitExceededError,
    StripeNotConfiguredError,
    InvalidStripeWebhookError,
)
from app.services.plan_limits import PLANS, PlanLimits, get_plan

if TYPE_CHECKING:
    from app.models.user import User

_LOG = get_logger(__name__)

_PAID_PLANS = {"pro", "business", "enterprise"}


class BillingService:
    def __init__(
        self,
        sub_repo: SubscriptionRepository,
        user_repo: UserRepository,
        settings: Settings,
        redis_client: Any | None = None,
    ) -> None:
        self._sub = sub_repo
        self._users = user_repo
        self._settings = settings
        self._redis = redis_client

    # ------------------------------------------------------------------
    # Subscription access helpers
    # ------------------------------------------------------------------

    async def get_or_create_subscription(self, user: "User") -> Subscription:
        """Return the user's subscription row, auto-provisioning FREE if absent."""
        sub = await self._sub.get_by_user_id(user.id)
        if sub is None:
            sub = await self._sub.create_free(user.id)
            await self._sub.commit()
            _LOG.info("subscription_provisioned_free", user_id=str(user.id))
        return sub

    async def get_plan_limits(self, user: "User") -> PlanLimits:
        """Return the PlanLimits for the user's active subscription."""
        sub = await self.get_or_create_subscription(user)
        return get_plan(sub.plan_slug.value)

    def get_plan_by_slug(self, slug: str) -> PlanLimits:
        if slug not in PLANS:
            raise PlanNotFoundError(f"Plan '{slug}' does not exist")
        return PLANS[slug]

    # ------------------------------------------------------------------
    # Limit enforcement (raise on violation)
    # ------------------------------------------------------------------

    async def enforce_bot_limit(self, user: "User", current_bot_count: int) -> None:
        """Raise BotLimitExceededError if user cannot create another bot."""
        limits = await self.get_plan_limits(user)
        if not limits.allows_bots(current_bot_count):
            _LOG.warning(
                "bot_limit_exceeded",
                user_id=str(user.id),
                plan=limits.slug,
                current=current_bot_count,
                max_allowed=limits.bots_max,
            )
            raise BotLimitExceededError(
                f"Your {limits.name} plan allows up to {limits.bots_max} bot(s). "
                f"You currently have {current_bot_count}. Upgrade to add more."
            )

    async def enforce_pdf_limit(self, user: "User", current_pdf_count: int) -> None:
        """Raise PdfLimitExceededError if user cannot upload another PDF."""
        limits = await self.get_plan_limits(user)
        if not limits.allows_pdfs(current_pdf_count):
            _LOG.warning(
                "pdf_limit_exceeded",
                user_id=str(user.id),
                plan=limits.slug,
                current=current_pdf_count,
                max_allowed=limits.pdf_files_max,
            )
            raise PdfLimitExceededError(
                f"Your {limits.name} plan allows up to {limits.pdf_files_max} knowledge file(s). "
                f"You currently have {current_pdf_count}. Upgrade to add more."
            )

    async def enforce_conversation_limit(
        self, user: "User", current_month_count: int
    ) -> None:
        """Raise ConversationLimitExceededError if monthly quota is exhausted."""
        limits = await self.get_plan_limits(user)
        if not limits.allows_conversations(current_month_count):
            _LOG.warning(
                "conversation_limit_exceeded",
                user_id=str(user.id),
                plan=limits.slug,
                current=current_month_count,
                max_allowed=limits.conversations_per_month,
            )
            raise ConversationLimitExceededError(
                f"Your {limits.name} plan allows {limits.conversations_per_month:,} conversation(s) "
                f"per month. You've used {current_month_count:,} this month."
            )

    async def enforce_storage_limit(
        self, user: "User", current_storage_mb: float
    ) -> None:
        """Raise StorageLimitExceededError if storage quota would be exceeded."""
        limits = await self.get_plan_limits(user)
        if limits.storage_mb is not None and current_storage_mb >= limits.storage_mb:
            raise StorageLimitExceededError(
                f"Your {limits.name} plan includes {limits.storage_mb:,} MB storage. "
                f"You've used {current_storage_mb:.1f} MB."
            )

    async def enforce_telegram_access(self, user: "User") -> None:
        """Raise ChannelNotAllowedError if user's plan doesn't include Telegram."""
        limits = await self.get_plan_limits(user)
        if not limits.allows_telegram():
            _LOG.warning(
                "telegram_channel_not_allowed",
                user_id=str(user.id),
                plan=limits.slug,
            )
            raise ChannelNotAllowedError(
                f"Telegram integration is not available on the {limits.name} plan. "
                f"Upgrade to Pro or higher to connect Telegram bots."
            )

    async def enforce_detailed_analytics(self, user: "User") -> None:
        """Raise AnalyticsNotAllowedError if user's plan doesn't include detailed analytics."""
        limits = await self.get_plan_limits(user)
        if not limits.allows_detailed_analytics():
            _LOG.warning(
                "detailed_analytics_not_allowed",
                user_id=str(user.id),
                plan=limits.slug,
            )
            raise AnalyticsNotAllowedError(
                f"Detailed analytics are not available on the {limits.name} plan. "
                f"Upgrade to Pro or higher for full analytics."
            )

    # ------------------------------------------------------------------
    # Stripe Checkout + Portal
    # ------------------------------------------------------------------

    def _stripe_module(self):  # type: ignore[return]
        """Lazy-import stripe so the app still boots when stripe is not installed."""
        try:
            import stripe  # type: ignore[import-untyped]
            return stripe
        except ImportError as exc:
            raise StripeNotConfiguredError(
                "stripe package is not installed. Run: pip install stripe"
            ) from exc

    def _require_stripe_keys(self) -> str:
        """Return Stripe secret key or raise StripeNotConfiguredError."""
        key = self._settings.stripe_secret_key
        if not key:
            raise StripeNotConfiguredError("STRIPE_SECRET_KEY is not configured.")
        # Detect placeholder values set in sample .env
        if key.startswith("sk_test_your") or key.endswith("_here") or "placeholder" in key.lower():
            raise StripeNotConfiguredError(
                "Stripe secret key is a placeholder. "
                "Set a real STRIPE_SECRET_KEY in your environment."
            )
        return key

    async def create_checkout_session(
        self,
        user: "User",
        plan_slug: str,
        *,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """
        Create a Stripe Checkout Session for upgrading to ``plan_slug``.
        Returns the session URL to redirect the user to.
        """
        stripe = self._stripe_module()
        secret_key = self._require_stripe_keys()
        stripe.api_key = secret_key

        if plan_slug not in PLANS:
            raise PlanNotFoundError(f"Plan '{plan_slug}' does not exist")
        if plan_slug == "free":
            raise PlanNotFoundError("Cannot checkout to the free plan.")

        price_id = self._settings.stripe_price_id_for(plan_slug)
        if not price_id:
            raise StripeNotConfiguredError(
                f"Stripe Price ID for plan '{plan_slug}' is not configured."
            )

        sub = await self.get_or_create_subscription(user)
        if sub.plan_slug.value == plan_slug and sub.status == SubscriptionStatus.active:
            raise AlreadyOnPlanError()

        # Reuse existing Stripe customer if we have one
        customer_id = sub.stripe_customer_id

        session_params: dict = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {
                "user_id": str(user.id),
                "plan_slug": plan_slug,
            },
            "subscription_data": {
                "metadata": {
                    "user_id": str(user.id),
                    "plan_slug": plan_slug,
                }
            },
        }
        if customer_id:
            session_params["customer"] = customer_id
        else:
            session_params["customer_email"] = user.email

        session = stripe.checkout.Session.create(**session_params)
        _LOG.info(
            "stripe_checkout_created",
            user_id=str(user.id),
            plan_slug=plan_slug,
            session_id=session.id,
        )
        return session.url

    async def create_portal_session(
        self,
        user: "User",
        *,
        return_url: str,
    ) -> str:
        """Create a Stripe Customer Portal session for managing billing."""
        stripe = self._stripe_module()
        secret_key = self._require_stripe_keys()
        stripe.api_key = secret_key

        sub = await self.get_or_create_subscription(user)
        if not sub.stripe_customer_id:
            raise StripeNotConfiguredError(
                "No Stripe customer linked to this account. "
                "Please subscribe to a paid plan first."
            )

        portal = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=return_url,
        )
        return portal.url

    async def cancel_subscription_for_deletion(self, user: "User") -> None:
        """Best-effort cancel Stripe subscription before account deletion."""
        sub = await self._sub.get_by_user_id(user.id)
        if not sub or not sub.stripe_subscription_id:
            return
        try:
            stripe = self._stripe_module()
            stripe.api_key = self._require_stripe_keys()
            stripe.Subscription.cancel(sub.stripe_subscription_id)
            _LOG.info(
                "stripe_subscription_canceled_for_deletion",
                user_id=str(user.id),
                stripe_sub_id=sub.stripe_subscription_id,
            )
        except Exception as exc:
            _LOG.warning(
                "stripe_cancel_failed_on_deletion",
                user_id=str(user.id),
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Stripe Webhook handler
    # ------------------------------------------------------------------

    async def handle_stripe_webhook(
        self, payload: bytes, sig_header: str
    ) -> None:
        """
        Verify and process a Stripe webhook event.
        Handles: checkout.session.completed, customer.subscription.updated,
                 customer.subscription.deleted, invoice.paid, invoice.payment_failed.
        """
        stripe = self._stripe_module()
        webhook_secret = self._settings.stripe_webhook_secret
        if not webhook_secret:
            raise InvalidStripeWebhookError("Stripe webhook secret is not configured.")

        secret_key = self._require_stripe_keys()
        stripe.api_key = secret_key

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except stripe.error.SignatureVerificationError as exc:
            _LOG.warning("stripe_webhook_signature_failed", error=str(exc))
            raise InvalidStripeWebhookError("Stripe signature verification failed.") from exc
        except Exception as exc:
            _LOG.warning("stripe_webhook_parse_failed", error=str(exc))
            raise InvalidStripeWebhookError("Failed to parse Stripe event.") from exc

        event_id = event["id"]
        event_type = event["type"]
        _LOG.info("stripe_webhook_received", event_type=event_type, event_id=event_id)

        if self._redis is not None:
            key = f"stripe:event:{event_id}"
            already = await self._redis.get(key)
            if already:
                _LOG.debug("stripe_webhook_duplicate_skipped", event_id=event_id)
                return

        try:
            if event_type == "checkout.session.completed":
                await self._on_checkout_completed(event["data"]["object"])
            elif event_type in (
                "customer.subscription.updated",
                "customer.subscription.created",
            ):
                await self._on_subscription_updated(event["data"]["object"])
            elif event_type == "customer.subscription.deleted":
                await self._on_subscription_deleted(event["data"]["object"])
            elif event_type == "invoice.paid":
                await self._on_invoice_paid(event["data"]["object"])
            elif event_type == "invoice.payment_failed":
                await self._on_invoice_payment_failed(event["data"]["object"])
            else:
                _LOG.debug("stripe_webhook_ignored", event_type=event_type)
        except Exception as exc:
            _LOG.error(
                "stripe_webhook_handler_error",
                event_type=event_type,
                event_id=event_id,
                error=str(exc),
            )
            raise

        if self._redis is not None:
            await self._redis.setex(f"stripe:event:{event_id}", 172800, b"1")

    async def _resolve_user_id_from_metadata(
        self, metadata: dict
    ) -> uuid.UUID | None:
        """Extract user_id UUID from Stripe metadata dict."""
        raw = metadata.get("user_id")
        if not raw:
            return None
        try:
            return uuid.UUID(str(raw))
        except ValueError:
            return None

    async def _resolve_plan_from_price(self, price_id: str | None) -> PlanSlug:
        """Map a Stripe Price ID back to a PlanSlug (falls back to FREE)."""
        if not price_id:
            return PlanSlug.free
        for slug in ("pro", "business", "enterprise"):
            if self._settings.stripe_price_id_for(slug) == price_id:
                return PlanSlug(slug)
        _LOG.warning("stripe_unknown_price_id", price_id=price_id)
        return PlanSlug.free

    async def _on_checkout_completed(self, session: dict) -> None:
        metadata = session.get("metadata") or {}
        user_id = await self._resolve_user_id_from_metadata(metadata)
        if not user_id:
            _LOG.warning("stripe_checkout_no_user_id", session_id=session.get("id"))
            return

        stripe_customer_id = session.get("customer")
        stripe_subscription_id = session.get("subscription")
        plan_slug_str = metadata.get("plan_slug", "free")

        try:
            plan_slug = PlanSlug(plan_slug_str)
        except ValueError:
            plan_slug = PlanSlug.free

        await self._sub.upsert_from_stripe(
            user_id=user_id,
            plan_slug=plan_slug,
            status=SubscriptionStatus.active,
            stripe_customer_id=stripe_customer_id or "",
            stripe_subscription_id=stripe_subscription_id or "",
            stripe_price_id=None,
            current_period_start=None,
            current_period_end=None,
        )
        await self._sub.commit()
        _LOG.info(
            "stripe_checkout_activated",
            user_id=str(user_id),
            plan=plan_slug_str,
        )

    async def _on_subscription_updated(self, stripe_sub: dict) -> None:
        metadata = stripe_sub.get("metadata") or {}
        user_id = await self._resolve_user_id_from_metadata(metadata)
        if not user_id:
            # Try to resolve via customer
            stripe_customer_id = stripe_sub.get("customer")
            if stripe_customer_id:
                existing = await self._sub.get_by_stripe_customer_id(stripe_customer_id)
                if existing:
                    user_id = existing.user_id
        if not user_id:
            _LOG.warning("stripe_sub_update_no_user", sub_id=stripe_sub.get("id"))
            return

        items_data = stripe_sub.get("items", {}).get("data", [])
        price_id = items_data[0]["price"]["id"] if items_data else None
        plan_slug = await self._resolve_plan_from_price(price_id)

        stripe_status = stripe_sub.get("status", "active")
        status_map = {
            "active": SubscriptionStatus.active,
            "trialing": SubscriptionStatus.trialing,
            "past_due": SubscriptionStatus.past_due,
            "canceled": SubscriptionStatus.canceled,
            "unpaid": SubscriptionStatus.past_due,
            "incomplete": SubscriptionStatus.past_due,
            "incomplete_expired": SubscriptionStatus.expired,
        }
        status = status_map.get(stripe_status, SubscriptionStatus.active)

        period_start = _ts_to_dt(stripe_sub.get("current_period_start"))
        period_end = _ts_to_dt(stripe_sub.get("current_period_end"))
        canceled_at = _ts_to_dt(stripe_sub.get("canceled_at"))

        await self._sub.upsert_from_stripe(
            user_id=user_id,
            plan_slug=plan_slug,
            status=status,
            stripe_customer_id=stripe_sub.get("customer", ""),
            stripe_subscription_id=stripe_sub.get("id", ""),
            stripe_price_id=price_id,
            current_period_start=period_start,
            current_period_end=period_end,
            canceled_at=canceled_at,
        )
        await self._sub.commit()
        _LOG.info(
            "stripe_subscription_updated",
            user_id=str(user_id),
            plan=plan_slug.value,
            status=status.value,
        )

    async def _on_subscription_deleted(self, stripe_sub: dict) -> None:
        stripe_sub_id = stripe_sub.get("id")
        if not stripe_sub_id:
            return

        existing = await self._sub.get_by_stripe_subscription_id(stripe_sub_id)
        if not existing:
            _LOG.warning(
                "stripe_sub_deleted_not_found", stripe_sub_id=stripe_sub_id
            )
            return

        await self._sub.downgrade_to_free(existing.user_id)
        await self._sub.commit()
        _LOG.info(
            "stripe_subscription_deleted_downgraded_free",
            user_id=str(existing.user_id),
        )

    async def _on_invoice_paid(self, invoice: dict) -> None:
        """Renew subscription period on successful payment."""
        stripe_sub_id = invoice.get("subscription")
        if not stripe_sub_id:
            return

        existing = await self._sub.get_by_stripe_subscription_id(stripe_sub_id)
        if not existing:
            return

        # Reactivate if was past_due
        if existing.status == SubscriptionStatus.past_due:
            existing.status = SubscriptionStatus.active
            await self._sub.commit()
            _LOG.info(
                "stripe_invoice_paid_reactivated",
                user_id=str(existing.user_id),
            )

    async def _on_invoice_payment_failed(self, invoice: dict) -> None:
        stripe_sub_id = invoice.get("subscription")
        if not stripe_sub_id:
            return

        existing = await self._sub.get_by_stripe_subscription_id(stripe_sub_id)
        if not existing:
            return

        existing.status = SubscriptionStatus.past_due
        await self._sub.commit()
        _LOG.warning(
            "stripe_invoice_payment_failed",
            user_id=str(existing.user_id),
        )


def _ts_to_dt(ts: int | float | None) -> datetime | None:
    """Convert Unix timestamp to timezone-aware datetime or None."""
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=UTC)
    except (ValueError, TypeError, OSError):
        return None
