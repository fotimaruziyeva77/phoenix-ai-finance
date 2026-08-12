"""Safe, compact logging for LLM provider boundaries (no prompts, completions, or secrets)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from structlog.stdlib import BoundLogger

from app.core.error_tracking import report_ai_provider_turn_failure


def log_ai_provider_call(
    log: BoundLogger,
    *,
    provider_name: str,
    model_name: str,
    success: bool,
    latency_ms: int,
    tokens_total: int | None,
    conversation_id: UUID | str,
    bot_id: UUID | str,
    channel: str | None = None,
    call_kind: str = "external",
    provider_error_code: str | None = None,
    ai_category: str | None = None,
    ai_step_kind: str | None = None,
    semantic_cache_hit: bool = False,
) -> None:
    """
    One structured line per provider boundary.

    ``call_kind``: ``external`` (HTTP/SDK to vendor), ``synthetic`` (no vendor I/O, e.g. lead-close text).
    """
    payload: dict[str, Any] = {
        "ai_provider": (provider_name or "").strip() or "unknown",
        "ai_model": (model_name or "").strip()[:128] or "unknown",
        "ai_success": success,
        "ai_latency_ms": latency_ms,
        "conversation_id": str(conversation_id),
        "bot_id": str(bot_id),
        "ai_call_kind": (call_kind or "external").strip()[:32],
    }
    if tokens_total is not None and tokens_total > 0:
        payload["ai_tokens_total"] = int(tokens_total)
    if channel and str(channel).strip():
        payload["channel"] = str(channel).strip()[:64]
    if provider_error_code and str(provider_error_code).strip():
        payload["provider_error_code"] = str(provider_error_code).strip()[:96]
    if ai_category and str(ai_category).strip():
        payload["ai_category"] = str(ai_category).strip()[:64]
    if ai_step_kind and str(ai_step_kind).strip():
        payload["ai_step_kind"] = str(ai_step_kind).strip()[:32]
    if semantic_cache_hit:
        payload["semantic_cache_hit"] = True

    emit = log.info if success else log.warning
    emit("ai_provider_call", **payload)
    report_ai_provider_turn_failure(
        success=success,
        provider_name=(provider_name or "").strip() or "unknown",
        provider_error_code=provider_error_code,
        ai_category=ai_category,
        conversation_id=str(conversation_id),
        bot_id=str(bot_id),
        channel=channel,
    )
