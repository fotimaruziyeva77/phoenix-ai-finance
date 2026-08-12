"""
Layer 4 — completion cache coordinator (exact Redis key → optional semantic embedding).

Order is fixed: **normalize → exact lookup → embed + semantic lookup**.
Trivial user turns must never reach this module (handled in :mod:`app.services.ai_chat_input_filter`).
"""

from __future__ import annotations

import uuid

from app.core.config import Settings
from app.core.logging import get_logger
from app.integrations.gemini_text_embedding import GeminiEmbeddingError
from app.services.semantic_completion_cache import (
    SemanticCompletionCache,
    exact_cache_turn_allowed,
    normalize_cache_message,
    semantic_cache_turn_allowed,
)

_LOG = get_logger(__name__)

CacheHitKind = str  # "exact" | "semantic"


async def try_completion_cache(
    cache: SemanticCompletionCache | None,
    settings: Settings,
    *,
    bot_id: uuid.UUID,
    conversation_state: str,
    raw_text: str,
    knowledge_injected: bool,
) -> tuple[str | None, CacheHitKind | None, str | None]:
    """
    Return ``(reply, hit_kind, embedding_error)``.

    * ``hit_kind == "exact"`` — Redis GET only (no embedding API).
    * ``hit_kind == "semantic"`` — embedding + cosine scan of the per-bot list.
    * ``embedding_error == "embedding_failed"`` — only returned when
      ``settings.ai_semantic_cache_strict_embedding`` is ``True``; callers must **not** invoke
      the chat LLM in that case.

    **Default (production-safe) behaviour**: embedding failures are logged and the cache step is
    silently skipped; the LLM path proceeds normally (``embedding_error`` is ``None``).
    Set ``AI_SEMANTIC_CACHE_STRICT_EMBEDDING=true`` only where you need to exercise the
    embedding-failure error path in tests.
    """
    dbg = bool(getattr(settings, "ai_pipeline_debug_trace_enabled", False))
    redis_configured = bool(
        ((settings.ai_semantic_cache_redis_url or "").strip() or (settings.rate_limit_redis_url or "").strip())
    )
    if dbg:
        _LOG.info(
            "ai_pipeline_debug",
            phase="completion_cache_enter",
            cache_client_present=cache is not None,
            redis_url_configured=redis_configured,
            ai_exact_cache_enabled=settings.ai_exact_cache_enabled,
            ai_semantic_cache_enabled=settings.ai_semantic_cache_enabled,
            knowledge_injected=knowledge_injected,
            inbound_chars=len((raw_text or "").strip()),
        )

    if cache is None:
        if dbg:
            _LOG.info(
                "ai_pipeline_debug",
                phase="completion_cache_skip",
                reason="cache_client_none",
            )
        return None, None, None

    norm = normalize_cache_message(raw_text)

    exact_allowed = exact_cache_turn_allowed(settings, raw_text, knowledge_injected=knowledge_injected)
    if dbg:
        _LOG.info(
            "ai_pipeline_debug",
            phase="before_exact_cache_lookup",
            normalized_cache_message=norm,
            exact_lookup_allowed=exact_allowed,
        )

    if exact_allowed:
        try:
            hit = await cache.lookup_exact(
                bot_id=bot_id,
                conversation_state=conversation_state,
                normalized_message=norm,
            )
            if hit:
                if dbg:
                    _LOG.info(
                        "ai_pipeline_debug",
                        phase="after_exact_cache_lookup",
                        hit=True,
                        hit_kind="exact",
                    )
                return hit, "exact", None
            if dbg:
                _LOG.info(
                    "ai_pipeline_debug",
                    phase="after_exact_cache_lookup",
                    hit=False,
                    hit_kind=None,
                )
        except Exception:
            _LOG.warning("exact_cache_lookup_failed", exc_info=True, bot_id=str(bot_id))
            if dbg:
                _LOG.info("ai_pipeline_debug", phase="after_exact_cache_lookup", hit=False, error=True)

    if not semantic_cache_turn_allowed(settings, raw_text, knowledge_injected=knowledge_injected):
        return None, None, None

    if dbg:
        _LOG.info("ai_pipeline_debug", phase="before_semantic_cache_embed")

    try:
        emb_q = await cache.embed_query(norm, fail_open=False)
    except GeminiEmbeddingError as exc:
        strict = bool(getattr(settings, "ai_semantic_cache_strict_embedding", False))
        if strict:
            _LOG.error(
                "semantic_cache_embedding_failed",
                bot_id=str(bot_id),
                conversation_state=conversation_state[:64],
                model_slug=exc.model_slug,
                http_status=exc.status_code,
                response_body_snippet=(exc.response_body_snippet or "")[:800],
                error_message=str(exc)[:500],
                strict_mode=True,
            )
            return None, None, "embedding_failed"
        # Non-strict (production-safe default): skip semantic cache, let LLM proceed.
        _LOG.warning(
            "semantic_cache_embedding_failed_continue",
            bot_id=str(bot_id),
            conversation_state=conversation_state[:64],
            model_slug=exc.model_slug,
            http_status=exc.status_code,
            error_message=str(exc)[:500],
            action="semantic_cache_skipped_due_to_embedding_error",
        )
        return None, None, None

    try:
        if not emb_q:
            if dbg:
                _LOG.info("ai_pipeline_debug", phase="after_semantic_cache_lookup", hit=False, reason="no_embedding")
            return None, None, None
        hit = await cache.lookup(
            bot_id=bot_id,
            conversation_state=conversation_state,
            normalized_message=norm,
            query_embedding=emb_q,
        )
        if hit:
            if dbg:
                _LOG.info(
                    "ai_pipeline_debug",
                    phase="after_semantic_cache_lookup",
                    hit=True,
                    hit_kind="semantic",
                )
            return hit, "semantic", None
        if dbg:
            _LOG.info("ai_pipeline_debug", phase="after_semantic_cache_lookup", hit=False, hit_kind=None)
    except Exception:
        _LOG.warning("semantic_cache_lookup_failed", exc_info=True, bot_id=str(bot_id))

    return None, None, None


async def remember_completion_caches(
    cache: SemanticCompletionCache | None,
    settings: Settings,
    *,
    bot_id: uuid.UUID,
    conversation_state: str,
    raw_user_text: str,
    normalized_message: str,
    response_text: str,
    knowledge_injected: bool,
) -> None:
    """Persist a successful assistant reply to exact (when allowed) and semantic (when allowed) stores."""
    if cache is None:
        return
    reply = (response_text or "").strip()
    if not reply:
        return

    if exact_cache_turn_allowed(settings, raw_user_text, knowledge_injected=knowledge_injected):
        try:
            await cache.remember_exact(
                bot_id=bot_id,
                conversation_state=conversation_state,
                normalized_message=normalized_message,
                response_text=reply,
            )
        except Exception:
            _LOG.warning("exact_cache_remember_failed", exc_info=True, bot_id=str(bot_id))

    if semantic_cache_turn_allowed(settings, raw_user_text, knowledge_injected=knowledge_injected):
        try:
            emb_store = await cache.embed_query(normalized_message)
            if emb_store:
                await cache.remember(
                    bot_id=bot_id,
                    conversation_state=conversation_state,
                    normalized_message=normalized_message,
                    embedding=emb_store,
                    response_text=reply,
                )
        except Exception:
            _LOG.warning("semantic_cache_remember_failed", exc_info=True, bot_id=str(bot_id))


__all__ = ["remember_completion_caches", "try_completion_cache"]
