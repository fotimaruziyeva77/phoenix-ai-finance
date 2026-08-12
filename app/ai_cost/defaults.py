"""
Baseline USD-per-million rates by ``provider`` → ``model_id`` (and ``*`` wildcard).

Override entirely or partially via ``APP_AI_PRICING_JSON``. Values are placeholders until
your finance team pins list prices; they are **not** imported by services directly.
"""

from __future__ import annotations

from decimal import Decimal

# (input_usd_per_million, output_usd_per_million)
_BUILTIN_GEMINI: dict[str, tuple[Decimal, Decimal]] = {
    # Wildcard fallback for unlisted Gemini model ids
    "*": (Decimal("0.075"), Decimal("0.30")),
    "gemini-2.0-flash-lite": (Decimal("0.075"), Decimal("0.30")),
    "gemini-2.5-flash": (Decimal("0.30"), Decimal("2.50")),
    "gemini-2.5-flash-lite": (Decimal("0.10"), Decimal("0.40")),
    "gemini-1.5-flash": (Decimal("0.075"), Decimal("0.30")),
    "gemini-1.5-flash-8b": (Decimal("0.0375"), Decimal("0.15")),
    "gemini-1.5-pro": (Decimal("1.25"), Decimal("5.00")),
}

DEFAULT_RATES_BY_PROVIDER: dict[str, dict[str, tuple[Decimal, Decimal]]] = {
    "gemini": _BUILTIN_GEMINI,
}
