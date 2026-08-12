"""Semantic cache Redis list + cosine (fakeredis)."""

from __future__ import annotations

import uuid

import fakeredis.aioredis as fakeredis
import pytest
from app.core.config import Settings
from app.services.semantic_completion_cache import SemanticCompletionCache, normalize_cache_message


@pytest.mark.asyncio
async def test_lookup_hits_when_cosine_high() -> None:
    s = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "dummy",
            "ai_semantic_cache_similarity_threshold": 0.9,
            "ai_semantic_cache_max_entries_per_bot": 50,
            "rate_limit_redis_url": "redis://localhost:6379/15",
        }
    )
    client = fakeredis.FakeRedis(decode_responses=True)
    bot_id = uuid.uuid4()
    cache = SemanticCompletionCache(settings=s, redis_url="redis://fake", redis_client=client)
    emb = [1.0, 0.0, 0.0]
    await cache.remember(
        bot_id=bot_id,
        conversation_state="start",
        normalized_message="salom",
        embedding=emb,
        response_text="cached hi",
    )
    hit = await cache.lookup(
        bot_id=bot_id,
        conversation_state="start",
        normalized_message="salom",
        query_embedding=[0.99, 0.01, 0.0],
    )
    assert hit == "cached hi"
    await cache.aclose()


def test_normalize_cache_message() -> None:
    assert normalize_cache_message("  Salom\n\n ") == "salom"


@pytest.mark.asyncio
async def test_maybe_create_disabled() -> None:
    s = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "k",
            "ai_semantic_cache_enabled": False,
            "ai_exact_cache_enabled": False,
        }
    )
    assert SemanticCompletionCache.maybe_create(s) is None


def test_maybe_create_exact_only_without_gemini_when_semantic_on() -> None:
    """Exact cache may use Redis even when semantic cache is enabled but no embedding API key."""
    s = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "",
            "ai_semantic_cache_enabled": True,
            "ai_exact_cache_enabled": True,
            "rate_limit_redis_url": "redis://localhost:6379/15",
        }
    )
    assert SemanticCompletionCache.maybe_create(s) is not None


def test_maybe_create_none_when_semantic_on_exact_off_and_no_gemini() -> None:
    s = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "",
            "ai_semantic_cache_enabled": True,
            "ai_exact_cache_enabled": False,
            "rate_limit_redis_url": "redis://localhost:6379/15",
        }
    )
    assert SemanticCompletionCache.maybe_create(s) is None
