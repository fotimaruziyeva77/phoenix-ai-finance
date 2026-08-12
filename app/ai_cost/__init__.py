"""
Centralized token normalization, optional estimation, and USD cost from config-driven pricing.

* **Pricing**: :func:`~app.ai_cost.catalog.build_pricing_catalog` + ``APP_AI_PRICING_JSON`` overlay.
* **Math**: :func:`~app.ai_cost.calculator.normalize_usage`, :func:`~app.ai_cost.calculator.calculate_cost`.
"""

from app.ai_cost.calculator import (
    calculate_cost,
    estimate_tokens_from_messages,
    normalize_usage,
    safe_zero_usage,
)
from app.ai_cost.catalog import PricingCatalog, build_pricing_catalog
from app.ai_cost.types import CostBreakdown

__all__ = [
    "CostBreakdown",
    "PricingCatalog",
    "build_pricing_catalog",
    "calculate_cost",
    "estimate_tokens_from_messages",
    "normalize_usage",
    "safe_zero_usage",
]
