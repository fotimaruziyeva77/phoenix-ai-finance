"""Domain errors for billing/subscription flows."""

from __future__ import annotations

from typing import ClassVar


class BillingError(Exception):
    """Base billing error with stable API code."""

    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "billing_error"
    default_message: ClassVar[str] = "Billing operation failed"

    def __init__(self, message: str | None = None) -> None:
        self.message: str = message or self.default_message
        super().__init__(self.message)


class PlanLimitExceededError(BillingError):
    """Raised when a user action would exceed their plan limits."""

    status_code = 402
    code = "plan_limit_exceeded"
    default_message = "Your current plan limit has been reached. Please upgrade to continue."


class BotLimitExceededError(PlanLimitExceededError):
    code = "bot_limit_exceeded"
    default_message = "You have reached the maximum number of bots for your plan."


class PdfLimitExceededError(PlanLimitExceededError):
    code = "pdf_limit_exceeded"
    default_message = "You have reached the maximum number of knowledge files for your plan."


class ConversationLimitExceededError(PlanLimitExceededError):
    code = "conversation_limit_exceeded"
    default_message = "Your monthly conversation limit has been reached. Please upgrade to continue."


class StorageLimitExceededError(PlanLimitExceededError):
    code = "storage_limit_exceeded"
    default_message = "You have reached the storage limit for your plan."


class StripeNotConfiguredError(BillingError):
    status_code = 503
    code = "stripe_not_configured"
    default_message = "Payment processing is not configured on this server."


class InvalidStripeWebhookError(BillingError):
    status_code = 400
    code = "invalid_stripe_webhook"
    default_message = "Invalid or unverifiable Stripe webhook payload."


class SubscriptionNotFoundError(BillingError):
    status_code = 404
    code = "subscription_not_found"
    default_message = "No active subscription found."


class PlanNotFoundError(BillingError):
    status_code = 404
    code = "plan_not_found"
    default_message = "The requested plan does not exist."


class AlreadyOnPlanError(BillingError):
    status_code = 409
    code = "already_on_plan"
    default_message = "You are already subscribed to this plan."


class ChannelNotAllowedError(PlanLimitExceededError):
    code = "channel_not_allowed"
    default_message = "Your current plan does not include this channel. Please upgrade to connect."


class AnalyticsNotAllowedError(PlanLimitExceededError):
    code = "analytics_not_allowed"
    default_message = "Detailed analytics require a paid plan. Please upgrade to access."
