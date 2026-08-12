"""
Token normalization, optional char-based estimation, and USD cost from :class:`~app.ai_cost.catalog.PricingCatalog`.

Services should call :func:`normalize_usage` / :func:`safe_zero_usage` and :func:`calculate_cost`
rather than embedding pricing math.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.ai_cost.catalog import PricingCatalog
from app.ai_cost.types import CostBreakdown
from app.ai_providers.types import ChatMessage

_QUANT = Decimal("0.00000001")


def _coerce_nonneg_int(value: object) -> int:
    """Parse usage counters from provider payloads; invalid values become 0."""
    if value is None:
        return 0
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, n)


def safe_zero_usage(
    tokens_input: int | None,
    tokens_output: int | None,
    tokens_total: int | None,
) -> tuple[int, int, int]:
    """Coerce negatives and ``None`` to zero for safe accounting."""
    inp = _coerce_nonneg_int(tokens_input)
    out = _coerce_nonneg_int(tokens_output)
    tot = _coerce_nonneg_int(tokens_total)
    return (inp, out, tot)


def normalize_usage(
    tokens_input: int | None,
    tokens_output: int | None,
    tokens_total: int | None,
) -> tuple[int, int, int]:
    """
    Normalize provider usage: non-negative ints; if ``tokens_total`` is missing but in/out exist, sum them.
    """
    inp, out, tot = safe_zero_usage(tokens_input, tokens_output, tokens_total)
    if tot == 0 and (inp > 0 or out > 0):
        tot = inp + out
    return (inp, out, tot)


def estimate_tokens_from_messages(
    *,
    messages: tuple[ChatMessage, ...],
    completion_text: str,
    chars_per_token: float,
) -> tuple[int, int]:
    """
    Rough token estimate when the provider omits counts (chars / divisor, floored).

    Not a substitute for tokenizer-based billing; central hook to swap for tiktoken later.
    """
    if chars_per_token <= 0:
        chars_per_token = 4.0
    prompt_chars = sum(len(m.content or "") for m in messages)
    out_chars = len(completion_text or "")
    inp = int(prompt_chars / chars_per_token)
    out = int(out_chars / chars_per_token)
    return (max(0, inp), max(0, out))


def calculate_cost(
    *,
    provider_name: str,
    model_name: str,
    tokens_input: int,
    tokens_output: int,
    tokens_total: int | None = None,
    catalog: PricingCatalog,
    used_token_estimation: bool = False,
) -> CostBreakdown:
    """
    Compute total tokens and USD cost from normalized counts and catalog rates.

    If no rate applies, ``cost_usd`` is ``None`` and ``pricing_matched`` is False.
    """
    inp, out, tot = normalize_usage(tokens_input, tokens_output, tokens_total)
    rates = catalog.resolve_usd_per_million(provider_name=provider_name, model_name=model_name)
    if rates is None or tot == 0:
        return CostBreakdown(
            tokens_input=inp,
            tokens_output=out,
            tokens_total=tot,
            cost_usd=None if rates is None else Decimal("0"),
            pricing_matched=rates is not None,
            used_token_estimation=used_token_estimation,
        )
    rin, rout = rates
    million = Decimal("1000000")
    cost = (Decimal(inp) * rin / million + Decimal(out) * rout / million).quantize(_QUANT, ROUND_HALF_UP)
    return CostBreakdown(
        tokens_input=inp,
        tokens_output=out,
        tokens_total=tot,
        cost_usd=cost,
        pricing_matched=True,
        used_token_estimation=used_token_estimation,
    )
