"""
Exact-cache hardening tests.

Coverage
--------
* Repeated identical message → exact cache hit (no LLM, no embedding).
* Exact cache operates when semantic cache is disabled.
* Exact cache hit is returned before embed_query is ever called.
* Cache miss falls through with (None, None, None) so the LLM is called.
* maybe_create returns a usable instance when semantic is disabled but exact is enabled.
* Observability: exact_cache_hit / exact_cache_miss / exact_cache_store are emitted.
* Key normalisation: different capitalisation / whitespace → same cache entry.
* Expired entries are ignored and log exact_cache_miss with reason="expired".

All Redis I/O uses fakeredis (no real Redis required).
"""

from __future__ import annotations

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis as fakeredis
import pytest

from app.core.config import Settings
from app.integrations.gemini_text_embedding import GeminiEmbeddingError
from app.services.ai_completion_cache import remember_completion_caches, try_completion_cache
from app.services.semantic_completion_cache import (
    SemanticCompletionCache,
    normalize_cache_message,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _settings(
    *,
    exact: bool = True,
    semantic: bool = False,
    gemini_key: str = "",
    redis_url: str = "redis://localhost:6379/15",
) -> Settings:
    """Minimal Settings for exact-cache tests.  Semantic off by default."""
    return Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": gemini_key,
            "ai_exact_cache_enabled": exact,
            "ai_semantic_cache_enabled": semantic,
            "rate_limit_redis_url": redis_url,
        }
    )


def _cache(settings: Settings, client: fakeredis.FakeRedis) -> SemanticCompletionCache:
    return SemanticCompletionCache(
        settings=settings,
        redis_url="redis://fake",
        redis_client=client,
    )


# ---------------------------------------------------------------------------
# 1. Repeated identical message returns from exact cache
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repeated_message_returns_from_exact_cache() -> None:
    """Store a reply, then verify the second call returns it without hitting LLM."""
    s = _settings(exact=True, semantic=False)
    client = fakeredis.FakeRedis(decode_responses=True)
    cache = _cache(s, client)
    bot_id = uuid.uuid4()
    norm = normalize_cache_message("Hello, what is your price?")

    await cache.remember_exact(
        bot_id=bot_id,
        conversation_state="open",
        normalized_message=norm,
        response_text="Our pricing starts at $29/month.",
    )

    hit = await cache.lookup_exact(
        bot_id=bot_id,
        conversation_state="open",
        normalized_message=norm,
    )
    assert hit == "Our pricing starts at $29/month."
    await cache.aclose()


@pytest.mark.asyncio
async def test_repeated_message_via_coordinator_returns_exact_hit() -> None:
    """Full coordinator path: second identical message hits exact cache, embed never called."""
    s = _settings(exact=True, semantic=False)
    client = fakeredis.FakeRedis(decode_responses=True)
    cache = _cache(s, client)
    bot_id = uuid.uuid4()
    raw_text = "  Hello, what is your price?  "
    norm = normalize_cache_message(raw_text)

    # Seed the cache as if the LLM already answered once.
    await cache.remember_exact(
        bot_id=bot_id,
        conversation_state="open",
        normalized_message=norm,
        response_text="Our pricing starts at $29/month.",
    )

    hit, kind, emb_err = await try_completion_cache(
        cache,
        s,
        bot_id=bot_id,
        conversation_state="open",
        raw_text=raw_text,
        knowledge_injected=False,
    )
    assert hit == "Our pricing starts at $29/month."
    assert kind == "exact"
    assert emb_err is None
    await cache.aclose()


# ---------------------------------------------------------------------------
# 2. Exact cache works when semantic cache is disabled
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exact_cache_works_when_semantic_disabled() -> None:
    """semantic=False, exact=True, no Gemini key — lookup_exact still returns hits."""
    s = _settings(exact=True, semantic=False, gemini_key="")
    client = fakeredis.FakeRedis(decode_responses=True)
    cache = _cache(s, client)
    bot_id = uuid.uuid4()
    norm = normalize_cache_message("salom")

    await cache.remember_exact(
        bot_id=bot_id,
        conversation_state="start",
        normalized_message=norm,
        response_text="Salom! Yordam bera olaman.",
    )
    hit = await cache.lookup_exact(
        bot_id=bot_id,
        conversation_state="start",
        normalized_message=norm,
    )
    assert hit == "Salom! Yordam bera olaman."
    await cache.aclose()


def test_maybe_create_returns_instance_when_semantic_disabled_exact_enabled() -> None:
    """maybe_create must not return None when only exact cache is needed."""
    s = _settings(exact=True, semantic=False, gemini_key="")
    result = SemanticCompletionCache.maybe_create(s)
    assert result is not None


def test_maybe_create_returns_none_when_both_disabled() -> None:
    s = _settings(exact=False, semantic=False)
    assert SemanticCompletionCache.maybe_create(s) is None


def test_maybe_create_returns_instance_when_semantic_enabled_no_gemini_key_but_exact_on() -> None:
    """semantic=True + no Gemini key + exact=True → instance created (exact still works)."""
    s = _settings(exact=True, semantic=True, gemini_key="")
    result = SemanticCompletionCache.maybe_create(s)
    assert result is not None


def test_maybe_create_returns_none_when_semantic_enabled_no_gemini_key_exact_disabled() -> None:
    """semantic=True + no Gemini key + exact=False → None (nothing useful to do)."""
    s = _settings(exact=False, semantic=True, gemini_key="")
    result = SemanticCompletionCache.maybe_create(s)
    assert result is None


# ---------------------------------------------------------------------------
# 3. Exact cache hit is returned before embed_query is ever called
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exact_hit_before_embedding_called() -> None:
    """When exact cache hits, embed_query must never be invoked."""
    s = _settings(exact=True, semantic=True, gemini_key="k")
    client = fakeredis.FakeRedis(decode_responses=True)
    cache = _cache(s, client)
    bot_id = uuid.uuid4()
    norm = normalize_cache_message("what is your price")

    await cache.remember_exact(
        bot_id=bot_id,
        conversation_state="open",
        normalized_message=norm,
        response_text="Cached price answer.",
    )

    # Patch embed_query to raise so the test fails loudly if it is called.
    cache.embed_query = AsyncMock(
        side_effect=AssertionError("embed_query must not be called on exact hit")
    )

    hit, kind, emb_err = await try_completion_cache(
        cache,
        s,
        bot_id=bot_id,
        conversation_state="open",
        raw_text="what is your price",
        knowledge_injected=False,
    )
    assert hit == "Cached price answer."
    assert kind == "exact"
    assert emb_err is None
    await cache.aclose()


@pytest.mark.asyncio
async def test_exact_hit_when_embedding_provider_raises() -> None:
    """Even if embed_query would raise GeminiEmbeddingError, exact hit is returned first."""
    s = _settings(exact=True, semantic=True, gemini_key="k")
    client = fakeredis.FakeRedis(decode_responses=True)
    cache = _cache(s, client)
    bot_id = uuid.uuid4()
    norm = normalize_cache_message("hello")

    await cache.remember_exact(
        bot_id=bot_id,
        conversation_state="greeting",
        normalized_message=norm,
        response_text="Hello reply.",
    )

    # Simulate embedding provider failure.
    cache.embed_query = AsyncMock(
        side_effect=GeminiEmbeddingError(
            "API down", status_code=503, model_slug="text-embedding-004"
        )
    )

    hit, kind, emb_err = await try_completion_cache(
        cache,
        s,
        bot_id=bot_id,
        conversation_state="greeting",
        raw_text="hello",
        knowledge_injected=False,
    )
    # Exact hit is returned before embed is reached.
    assert hit == "Hello reply."
    assert kind == "exact"
    assert emb_err is None
    # embed was never reached because exact hit returned first.
    cache.embed_query.assert_not_called()
    await cache.aclose()


# ---------------------------------------------------------------------------
# 4. Cache miss falls through correctly — (None, None, None) so LLM is called
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exact_cache_miss_returns_none_tuple() -> None:
    """Empty cache → (None, None, None) so the caller proceeds to LLM."""
    s = _settings(exact=True, semantic=False)
    client = fakeredis.FakeRedis(decode_responses=True)
    cache = _cache(s, client)

    hit, kind, emb_err = await try_completion_cache(
        cache,
        s,
        bot_id=uuid.uuid4(),
        conversation_state="open",
        raw_text="what is the enterprise pricing?",
        knowledge_injected=False,
    )
    assert hit is None
    assert kind is None
    assert emb_err is None
    await cache.aclose()


@pytest.mark.asyncio
async def test_different_bot_id_does_not_cross_contaminate() -> None:
    """Cache is scoped per bot — bot A's entry must not be returned for bot B."""
    s = _settings(exact=True, semantic=False)
    client = fakeredis.FakeRedis(decode_responses=True)
    bot_a = uuid.uuid4()
    bot_b = uuid.uuid4()
    norm = normalize_cache_message("what is your price")
    cache = _cache(s, client)

    await cache.remember_exact(
        bot_id=bot_a,
        conversation_state="open",
        normalized_message=norm,
        response_text="Bot A answer.",
    )
    hit = await cache.lookup_exact(
        bot_id=bot_b,
        conversation_state="open",
        normalized_message=norm,
    )
    assert hit is None, "Bot B must not see Bot A's cache entry"
    await cache.aclose()


@pytest.mark.asyncio
async def test_different_conversation_state_does_not_cross_contaminate() -> None:
    """Cache keys include conversation state — same message in different state → miss."""
    s = _settings(exact=True, semantic=False)
    client = fakeredis.FakeRedis(decode_responses=True)
    bot_id = uuid.uuid4()
    norm = normalize_cache_message("pricing")
    cache = _cache(s, client)

    await cache.remember_exact(
        bot_id=bot_id,
        conversation_state="state_A",
        normalized_message=norm,
        response_text="State A answer.",
    )
    hit = await cache.lookup_exact(
        bot_id=bot_id,
        conversation_state="state_B",
        normalized_message=norm,
    )
    assert hit is None
    await cache.aclose()


# ---------------------------------------------------------------------------
# 5. Key normalisation — whitespace / case → same cache entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_normalised_key_matches_original_capitalised_input() -> None:
    """'  Hello World  ' and 'hello world' must resolve to the same cache entry."""
    s = _settings(exact=True, semantic=False)
    client = fakeredis.FakeRedis(decode_responses=True)
    cache = _cache(s, client)
    bot_id = uuid.uuid4()

    norm_a = normalize_cache_message("  Hello World  ")
    norm_b = normalize_cache_message("hello world")
    assert norm_a == norm_b, "normalisation contract broken"

    await cache.remember_exact(
        bot_id=bot_id,
        conversation_state="open",
        normalized_message=norm_a,
        response_text="Consistent reply.",
    )
    hit = await cache.lookup_exact(
        bot_id=bot_id,
        conversation_state="open",
        normalized_message=norm_b,
    )
    assert hit == "Consistent reply."
    await cache.aclose()


# ---------------------------------------------------------------------------
# 6. Expired entries are treated as misses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expired_entry_is_treated_as_miss() -> None:
    """An entry whose exp timestamp is in the past must not be returned."""
    import json

    s = _settings(exact=True, semantic=False)
    client = fakeredis.FakeRedis(decode_responses=True)
    cache = _cache(s, client)
    bot_id = uuid.uuid4()
    norm = normalize_cache_message("expired question")

    # Write an already-expired entry directly (bypass remember_exact TTL logic).
    from app.services.semantic_completion_cache import _exact_cache_redis_key
    key = _exact_cache_redis_key(s, bot_id, "open", norm)
    expired_row = {"r": "should not be returned", "exp": time.time() - 10.0}
    r = await cache._client()
    await r.set(key, json.dumps(expired_row))

    hit = await cache.lookup_exact(
        bot_id=bot_id,
        conversation_state="open",
        normalized_message=norm,
    )
    assert hit is None
    await cache.aclose()


# ---------------------------------------------------------------------------
# 7. remember_completion_caches writes exact independently of semantic path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remember_exact_independent_of_semantic_failure() -> None:
    """
    remember_completion_caches must write exact cache even when the semantic
    remember path fails (e.g. embed_query raises).
    """
    s = _settings(exact=True, semantic=True, gemini_key="k")
    client = fakeredis.FakeRedis(decode_responses=True)
    cache = _cache(s, client)
    bot_id = uuid.uuid4()
    raw_text = "show me the pricing"
    norm = normalize_cache_message(raw_text)

    # Patch embed_query to simulate embedding failure during remember.
    cache.embed_query = AsyncMock(
        side_effect=RuntimeError("embedding API down during store")
    )

    await remember_completion_caches(
        cache,
        s,
        bot_id=bot_id,
        conversation_state="open",
        raw_user_text=raw_text,
        normalized_message=norm,
        response_text="Pricing: $29/month.",
        knowledge_injected=False,
    )

    # Exact cache must have been written despite semantic failure.
    hit = await cache.lookup_exact(
        bot_id=bot_id,
        conversation_state="open",
        normalized_message=norm,
    )
    assert hit == "Pricing: $29/month."
    await cache.aclose()


# ---------------------------------------------------------------------------
# 8. Observability log events are emitted at the correct level
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exact_cache_hit_log_emitted(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    s = _settings(exact=True, semantic=False)
    client = fakeredis.FakeRedis(decode_responses=True)
    cache = _cache(s, client)
    bot_id = uuid.uuid4()
    norm = normalize_cache_message("log test message")

    await cache.remember_exact(
        bot_id=bot_id, conversation_state="s", normalized_message=norm, response_text="reply"
    )
    with caplog.at_level(logging.INFO, logger="app.services.semantic_completion_cache"):
        await cache.lookup_exact(bot_id=bot_id, conversation_state="s", normalized_message=norm)

    assert any("exact_cache_hit" in r.message for r in caplog.records)
    await cache.aclose()


@pytest.mark.asyncio
async def test_exact_cache_miss_log_emitted(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    s = _settings(exact=True, semantic=False)
    client = fakeredis.FakeRedis(decode_responses=True)
    cache = _cache(s, client)
    norm = normalize_cache_message("not stored")

    with caplog.at_level(logging.DEBUG, logger="app.services.semantic_completion_cache"):
        await cache.lookup_exact(
            bot_id=uuid.uuid4(), conversation_state="s", normalized_message=norm
        )

    assert any("exact_cache_miss" in r.message for r in caplog.records)
    await cache.aclose()


@pytest.mark.asyncio
async def test_exact_cache_store_log_emitted(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    s = _settings(exact=True, semantic=False)
    client = fakeredis.FakeRedis(decode_responses=True)
    cache = _cache(s, client)
    norm = normalize_cache_message("store test")

    with caplog.at_level(logging.DEBUG, logger="app.services.semantic_completion_cache"):
        await cache.remember_exact(
            bot_id=uuid.uuid4(),
            conversation_state="s",
            normalized_message=norm,
            response_text="stored reply",
        )

    assert any("exact_cache_store" in r.message for r in caplog.records)
    await cache.aclose()
