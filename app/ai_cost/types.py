"""Value types for usage normalization and cost breakdown."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    """Financial view for one inference call (persist to messages / usage logs)."""

    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: Decimal | None
    """None when no pricing rule matched (still measurable by tokens)."""
    pricing_matched: bool
    used_token_estimation: bool
    """True when tokens came from char-based fallback, not the provider."""
