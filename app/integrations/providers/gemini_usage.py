"""
Gemini usage metadata → :class:`~app.ai_providers.types.TokenUsage` and estimation hooks.
"""

from __future__ import annotations

from typing import Any, Mapping

from app.ai_providers.types import NormalizedAIResult, TokenUsage


def parse_gemini_usage_metadata(raw: Mapping[str, Any] | None) -> TokenUsage | None:
    """
    Parse ``usageMetadata`` from a generateContent JSON object.

    Accepts camelCase (REST) and optional snake_case keys for resilience.
    """
    if not raw:
        return None
    inp = raw.get("promptTokenCount")
    if inp is None:
        inp = raw.get("prompt_token_count")
    out = raw.get("candidatesTokenCount")
    if out is None:
        out = raw.get("candidates_token_count")
    total = raw.get("totalTokenCount")
    if total is None:
        total = raw.get("total_token_count")
    if inp is None and out is None and total is None:
        return None
    try:
        return TokenUsage(
            input_tokens=int(inp) if inp is not None else None,
            output_tokens=int(out) if out is not None else None,
            total_tokens=int(total) if total is not None else None,
        )
    except (TypeError, ValueError):
        return None


def usage_estimation_recommended(result: NormalizedAIResult) -> bool:
    """
    True when the call succeeded with text but no usable token counts.

    Downstream jobs can attach estimators (e.g. char-based) without changing the provider.
    """
    if not result.success or not result.text:
        return False
    if result.tokens is None:
        return True
    t = result.tokens
    return t.input_tokens is None and t.output_tokens is None and t.total_tokens is None
