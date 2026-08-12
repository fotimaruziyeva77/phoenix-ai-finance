"""
Dashboard-ready observability for the AI chat pipeline (structured logs + DB alignment).

Each user turn emits exactly one ``ai_pipeline_turn`` log event with stable field names so
log aggregators (Datadog, CloudWatch, Loki) can compute cache rates, token volume, and cost
without scraping prompts or completions.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Any
from uuid import UUID

from structlog.stdlib import BoundLogger

from app.core.error_tracking import report_ai_provider_turn_failure

# --- Canonical step_kind values (must fit ai_usage_logs.step_kind VARCHAR(32)) ---
STEP_TRIVIAL_HANDLED = "trivial_handled"
STEP_EXACT_CACHE_HIT = "exact_cache_hit"
STEP_SEMANTIC_CACHE_HIT = "semantic_cache_hit"
STEP_LLM_CALL = "llm_call"
# Sales / lead flows that never call the chat completion model
STEP_SYNTHETIC_OUTPUT = "synthetic_output"

# --- cache_type for logs (not stored on ai_usage_logs; derive from step_kind in SQL) ---
CACHE_TYPE_NONE = "none"
CACHE_TYPE_EXACT = "exact"
CACHE_TYPE_SEMANTIC = "semantic"


def cache_type_for_step(step_kind: str) -> str:
    if step_kind == STEP_EXACT_CACHE_HIT:
        return CACHE_TYPE_EXACT
    if step_kind == STEP_SEMANTIC_CACHE_HIT:
        return CACHE_TYPE_SEMANTIC
    return CACHE_TYPE_NONE


def rough_token_estimate_chars_div4(text: str, *, chars_per_token: float = 4.0) -> int:
    """Provider-agnostic token hint: ``ceil(chars / chars_per_token)`` floored to int (spec: ~len/4)."""
    cpt = float(chars_per_token) if float(chars_per_token) > 0 else 4.0
    return max(0, int(len(text or "") / cpt))


def estimate_tokens_saved_vs_llm(
    *,
    user_text: str,
    history_message_contents: Sequence[str],
    assistant_reply: str,
    system_prompt_char_budget: int,
    chars_per_token: float = 4.0,
) -> int:
    """
    Heuristic tokens **not** sent to the vendor LLM on cache/trivial paths.

    Uses character counts only (no tokenizer): ``(history + user + system_budget) / cpt + reply / cpt``.
    """
    cpt = float(chars_per_token) if float(chars_per_token) > 0 else 4.0
    hist_chars = sum(len((c or "")) for c in history_message_contents)
    inp_chars = hist_chars + len(user_text or "") + max(0, int(system_prompt_char_budget))
    out_chars = len(assistant_reply or "")
    return max(0, int(inp_chars / cpt) + int(out_chars / cpt))


def track_ai_usage(
    log: BoundLogger,
    *,
    bot_id: UUID | str,
    conversation_id: UUID | str | None,
    channel: str | None,
    step_kind: str,
    provider_name: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    estimated_cost_usd: Decimal | float | None,
    response_time_ms: int,
    cache_type: str,
    tokens_saved_est: int | None = None,
    success: bool = True,
    used_token_estimation: bool = False,
    error_code: str | None = None,
    failure_category: str | None = None,
) -> None:
    """
    Emit one ``ai_pipeline_turn`` structured log per request (trivial, cache hit, or LLM).

    Postgres ``ai_usage_logs`` should be written separately with the same ``step_kind`` and
    token/cost columns for warehouse joins.
    """
    cost_val: float | None
    if estimated_cost_usd is None:
        cost_val = None
    elif isinstance(estimated_cost_usd, Decimal):
        cost_val = float(estimated_cost_usd)
    else:
        cost_val = float(estimated_cost_usd)

    payload: dict[str, Any] = {
        "step_kind": (step_kind or "").strip()[:32] or "unknown",
        "input_tokens": max(0, int(input_tokens)),
        "output_tokens": max(0, int(output_tokens)),
        "total_tokens": max(0, int(total_tokens)),
        "estimated_cost_usd": cost_val,
        "response_time_ms": max(0, int(response_time_ms)),
        "cache_type": (cache_type or CACHE_TYPE_NONE).strip()[:16],
        "bot_id": str(bot_id),
        "conversation_id": str(conversation_id) if conversation_id is not None else None,
        "provider_name": (provider_name or "").strip()[:64] or "unknown",
        "model_name": (model_name or "").strip()[:128] or "unknown",
        "pipeline_success": bool(success),
        "used_token_estimation": bool(used_token_estimation),
    }
    if channel and str(channel).strip():
        payload["channel"] = str(channel).strip()[:64]
    if tokens_saved_est is not None and tokens_saved_est > 0:
        payload["tokens_saved_est"] = int(tokens_saved_est)
    if error_code and str(error_code).strip():
        payload["error_code"] = str(error_code).strip()[:96]

    emit = log.info if success else log.warning
    emit("ai_pipeline_turn", **payload)

    report_ai_provider_turn_failure(
        success=success,
        provider_name=(provider_name or "").strip() or "unknown",
        provider_error_code=error_code,
        ai_category=failure_category,
        conversation_id=str(conversation_id) if conversation_id is not None else "",
        bot_id=str(bot_id),
        channel=channel,
    )


__all__ = [
    "CACHE_TYPE_EXACT",
    "CACHE_TYPE_NONE",
    "CACHE_TYPE_SEMANTIC",
    "STEP_EXACT_CACHE_HIT",
    "STEP_LLM_CALL",
    "STEP_SEMANTIC_CACHE_HIT",
    "STEP_SYNTHETIC_OUTPUT",
    "STEP_TRIVIAL_HANDLED",
    "cache_type_for_step",
    "estimate_tokens_saved_vs_llm",
    "rough_token_estimate_chars_div4",
    "track_ai_usage",
]
