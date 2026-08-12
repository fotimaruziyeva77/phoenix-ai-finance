"""Static plan catalogue — single source of truth for limits and pricing.

Plans are defined in code (not DB) for zero-latency entitlement checks.
Stripe Price IDs are read from ``Settings`` at runtime so they can be
configured per-environment via ``.env`` without code changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class PlanLimits:
    """Immutable limits descriptor for one pricing tier."""

    slug: str
    name: str
    price_cents: int  # USD cents per month (0 = free)

    # None → unlimited
    conversations_per_month: Optional[int]
    bots_max: Optional[int]
    pdf_files_max: Optional[int]
    storage_mb: Optional[int]

    # Channel access
    telegram_allowed: bool = field(default=False)

    # Analytics depth: "basic" = usage summary only, "detailed" = full breakdown
    analytics_detailed: bool = field(default=False)

    # Widget branding: True = "Powered by BotForge" badge shown
    show_branding: bool = field(default=True)

    # Human-readable description shown in billing UI
    tagline: str = field(default="")
    is_popular: bool = field(default=False)

    def is_unlimited_bots(self) -> bool:
        return self.bots_max is None

    def is_unlimited_conversations(self) -> bool:
        return self.conversations_per_month is None

    def is_unlimited_pdfs(self) -> bool:
        return self.pdf_files_max is None

    def is_unlimited_storage(self) -> bool:
        return self.storage_mb is None

    def allows_bots(self, current_count: int) -> bool:
        return self.bots_max is None or current_count < self.bots_max

    def allows_pdfs(self, current_count: int) -> bool:
        return self.pdf_files_max is None or current_count < self.pdf_files_max

    def allows_conversations(self, current_month_count: int) -> bool:
        return self.conversations_per_month is None or current_month_count < self.conversations_per_month

    def allows_telegram(self) -> bool:
        return self.telegram_allowed

    def allows_detailed_analytics(self) -> bool:
        return self.analytics_detailed

    def price_dollars(self) -> float:
        return self.price_cents / 100


# -----------------------------------------------------------------------
# Canonical plan catalogue
# -----------------------------------------------------------------------
# Keep in sync with app.models.enums.PlanSlug values.

PLANS: dict[str, PlanLimits] = {
    "free": PlanLimits(
        slug="free",
        name="Free",
        price_cents=0,
        conversations_per_month=100,
        bots_max=1,
        pdf_files_max=1,
        storage_mb=5,
        telegram_allowed=False,
        analytics_detailed=False,
        show_branding=True,
        tagline="Try BotForge AI with no commitment",
    ),
    "pro": PlanLimits(
        slug="pro",
        name="Pro",
        price_cents=3_900,
        conversations_per_month=5_000,
        bots_max=5,
        pdf_files_max=25,
        storage_mb=500,
        telegram_allowed=True,
        analytics_detailed=True,
        show_branding=False,
        tagline="For businesses ready to capture leads at scale",
        is_popular=True,
    ),
    "business": PlanLimits(
        slug="business",
        name="Business",
        price_cents=9_900,
        conversations_per_month=20_000,
        bots_max=None,
        pdf_files_max=None,
        storage_mb=5_000,
        telegram_allowed=True,
        analytics_detailed=True,
        show_branding=False,
        tagline="For teams that need full power and flexibility",
    ),
    "enterprise": PlanLimits(
        slug="enterprise",
        name="Enterprise",
        price_cents=0,
        conversations_per_month=None,
        bots_max=None,
        pdf_files_max=None,
        storage_mb=None,
        telegram_allowed=True,
        analytics_detailed=True,
        show_branding=False,
        tagline="Custom volume, SLA, and dedicated support",
    ),
}

PLAN_ORDER: list[str] = ["free", "pro", "business", "enterprise"]


def get_plan(slug: str) -> PlanLimits:
    """Return plan by slug; falls back to FREE for unknown slugs (safe default)."""
    return PLANS.get(slug, PLANS["free"])


def get_all_plans() -> list[PlanLimits]:
    """Ordered plan list for billing UI."""
    return [PLANS[s] for s in PLAN_ORDER]
