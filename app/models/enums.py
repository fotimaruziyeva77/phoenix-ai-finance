"""Shared persistence enums (mirrored in PostgreSQL where native ENUM is used)."""

from enum import Enum


class UserRole(str, Enum):
    """
    Application roles (PostgreSQL ``user_role`` enum; keep values in sync with migrations).

    * ``customer_admin`` — default at signup; tenant/workspace scope for bots, leads, embeds.
    * ``superadmin`` — platform operator; use :mod:`app.core.rbac` + ``/api/v1/admin/*`` only.
      Must not imply cross-tenant access on owner-scoped routes without explicit admin handlers.
    """

    customer_admin = "customer_admin"
    superadmin = "superadmin"


class OAuthProvider(str, Enum):
    """Supported OAuth identity providers."""

    google = "google"
    github = "github"


class PlanSlug(str, Enum):
    """Subscription plan tiers (keep in sync with ``app.services.plan_limits.PLANS``)."""

    free = "free"
    starter = "starter"  # deprecated — kept for existing DB rows only
    pro = "pro"
    business = "business"
    enterprise = "enterprise"


class SubscriptionStatus(str, Enum):
    """Lifecycle states for a user subscription row."""

    active = "active"
    trialing = "trialing"
    past_due = "past_due"
    canceled = "canceled"
    expired = "expired"
