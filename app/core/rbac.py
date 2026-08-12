"""
Role-based access primitives for BotForge (explicit roles; no implicit elevation).

**Roles** (see :class:`~app.models.enums.UserRole`):

* ``customer_admin`` — tenant/workspace owner; all existing ``/api/v1/bots``, leads, widget,
  Telegram dashboard routes remain scoped to ``user.id`` as owner.
* ``superadmin`` — platform operator; may use ``/api/v1/admin/*`` and future cross-tenant APIs.
  Superadmin does **not** automatically gain other users' data through owner-scoped endpoints;
  those handlers continue to filter by ``owner_id == user.id`` unless a dedicated admin route
  is added and guarded with :func:`require_superadmin` (or equivalent).

**Capabilities** — named platform permissions for superadmin-only features (listing all tenants,
cross-tenant bot views, moderation). Use :func:`user_may` inside services or routes to avoid
scattered role string checks.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.user import User


def is_customer_admin(user: User) -> bool:
    return user.role == UserRole.customer_admin


def is_superadmin(user: User) -> bool:
    return user.role == UserRole.superadmin


class PlatformCapability(StrEnum):
    """Superadmin-gated capabilities (extend as platform admin features ship)."""

    VIEW_PLATFORM_DASHBOARD = "view_platform_dashboard"
    LIST_TENANTS = "list_tenants"
    LIST_BOTS_ALL_TENANTS = "list_bots_all_tenants"
    MODERATION_ACTIONS = "moderation_actions"


def _all_superadmin_capabilities() -> frozenset[PlatformCapability]:
    return frozenset(PlatformCapability)


def platform_capabilities_for(user: User) -> frozenset[PlatformCapability]:
    """Return capabilities for ``user`` (empty for non-superadmin)."""
    if is_superadmin(user):
        return _all_superadmin_capabilities()
    return frozenset()


def user_may(user: User, capability: PlatformCapability) -> bool:
    """True if ``user`` may perform ``capability`` (explicit check; prefer over raw role compares)."""
    return capability in platform_capabilities_for(user)


__all__ = [
    "PlatformCapability",
    "is_customer_admin",
    "is_superadmin",
    "platform_capabilities_for",
    "user_may",
]
