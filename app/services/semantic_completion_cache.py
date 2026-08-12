"""
Redis-backed semantic completion cache for short, repeatable user turns.

Uses Gemini ``embedContent`` vectors + cosine similarity (in-process scan of a small per-bot list).
Designed **fail-open**: Redis/embedding errors never block chat — they only skip cache.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any

import httpx
import redis.asyncio as redis

from app.core.config import Settings
from app.core.logging import get_logger
from app.integrations.gemini_text_embedding import gemini_embed_text
from app.lib.vector_cosine import cosine_similarity

_LOG = get_logger(__name__)


def exact_cache_turn_allowed(
    settings: Settings,
    text: str,
    *,
    knowledge_injected: bool = False,
) -> bool:
    """Exact string cache: broader than semantic (message length only), still skips RAG turns."""
    if not settings.ai_exact_cache_enabled:
        return False
    if knowledge_injected:
        return False
    t = (text or "").strip()
    if len(t) > int(settings.ai_exact_cache_max_message_chars):
        return False
    return True


def semantic_cache_turn_allowed(
    settings: Settings,
    text: str,
    *,
    knowledge_injected: bool = False,
) -> bool:
    """Whether a turn may use semantic cache (short message, no knowledge context in prompt)."""
    if not settings.ai_semantic_cache_enabled:
        return False
    if knowledge_injected:
        return False
    t = (text or "").strip()
    if len(t) > int(settings.ai_semantic_cache_max_message_chars):
        return False
    if len(t.split()) > int(settings.ai_semantic_cache_max_words):
        return False
    return True


def _redis_list_key(prefix: str, bot_id: uuid.UUID) -> str:
    p = (prefix or "bf:ai:sc").strip() or "bf:ai:sc"
    return f"{p}:v1:{bot_id}"


def normalize_cache_message(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _exact_cache_redis_key(settings: Settings, bot_id: uuid.UUID, conversation_state: str, norm: str) -> str:
    pref = (settings.ai_exact_cache_key_prefix or "bf:ai:ec").strip() or "bf:ai:ec"
    st = hashlib.sha256(conversation_state.encode("utf-8")).hexdigest()[:24]
    qs = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:24]
    return f"{pref}:v1:{bot_id}:{st}:{qs}"


class SemanticCompletionCache:
    """LRU-ish list in Redis (LPUSH + LTRIM); lookup scans entries for cosine >= threshold."""

    def __init__(
        self,
        *,
        settings: Settings,
        redis_url: str,
        redis_client: redis.Redis | None = None,
    ) -> None:
        self._settings = settings
        self._redis_url = redis_url
        self._owns_client = redis_client is None
        self._redis: redis.Redis | None = redis_client
        self._http: httpx.AsyncClient | None = None

    @classmethod
    def maybe_create(
        cls,
        settings: Settings,
        *,
        redis_client: redis.Redis | None = None,
    ) -> SemanticCompletionCache | None:
        if not settings.ai_semantic_cache_enabled and not settings.ai_exact_cache_enabled:
            return None
        url = (
            (settings.ai_semantic_cache_redis_url or "").strip()
            or (settings.rate_limit_redis_url or "").strip()
        )
        if not url:
            return None
        # Semantic embeddings require Gemini; exact-only cache can still use Redis alone.
        if settings.ai_semantic_cache_enabled and not (settings.gemini_api_key or "").strip():
            if not settings.ai_exact_cache_enabled:
                return None
        return cls(settings=settings, redis_url=url, redis_client=redis_client)

    async def _client(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=float(self._settings.rate_limit_redis_connect_timeout_seconds),
                socket_timeout=float(self._settings.rate_limit_redis_socket_timeout_seconds),
            )
        return self._redis

    async def _embed_client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self._settings.gemini_api_base_url.rstrip("/"),
                timeout=httpx.Timeout(30.0, connect=5.0),
            )
        return self._http

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        if self._owns_client and self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def lookup(
        self,
        *,
        bot_id: uuid.UUID,
        conversation_state: str,
        normalized_message: str,
        query_embedding: list[float],
    ) -> str | None:
        key = _redis_list_key(self._settings.ai_semantic_cache_key_prefix, bot_id)
        thr = float(self._settings.ai_semantic_cache_similarity_threshold)
        try:
            r = await self._client()
            raw_entries = await r.lrange(key, 0, int(self._settings.ai_semantic_cache_max_entries_per_bot) - 1)
        except redis.RedisError:
            _LOG.warning("semantic_cache_redis_read_failed", bot_id=str(bot_id))
            return None

        now = time.time()
        ttl = int(self._settings.ai_semantic_cache_entry_ttl_seconds)
        best: tuple[float, str] | None = None
        for raw in raw_entries:
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            if float(row.get("exp", 0) or 0) and now > float(row["exp"]):
                continue
            if str(row.get("st", "")) != conversation_state:
                continue
            emb = row.get("e")
            if not isinstance(emb, list):
                continue
            try:
                vec = [float(x) for x in emb]
            except (TypeError, ValueError):
                continue
            sim = cosine_similarity(query_embedding, vec)
            if sim < thr:
                continue
            txt = row.get("r")
            if not isinstance(txt, str) or not txt.strip():
                continue
            if best is None or sim > best[0]:
                best = (sim, txt.strip())

        if best is not None:
            _LOG.info(
                "semantic_cache_hit",
                bot_id=str(bot_id),
                conversation_state=conversation_state[:64],
                similarity=round(best[0], 4),
                query_chars=len(normalized_message),
            )
            return best[1]
        return None

    async def remember(
        self,
        *,
        bot_id: uuid.UUID,
        conversation_state: str,
        normalized_message: str,
        embedding: list[float],
        response_text: str,
    ) -> None:
        key = _redis_list_key(self._settings.ai_semantic_cache_key_prefix, bot_id)
        ttl = int(self._settings.ai_semantic_cache_entry_ttl_seconds)
        exp = (time.time() + float(ttl)) if ttl > 0 else 0.0
        row: dict[str, Any] = {
            "st": conversation_state[:128],
            "q": normalized_message[:512],
            "e": embedding,
            "r": (response_text or "")[:8000],
            "exp": exp,
        }
        try:
            payload = json.dumps(row, separators=(",", ":"))
            r = await self._client()
            max_n = int(self._settings.ai_semantic_cache_max_entries_per_bot)
            async with r.pipeline(transaction=True) as pipe:
                await pipe.lpush(key, payload)
                await pipe.ltrim(key, 0, max(0, max_n - 1))
                await pipe.execute()
        except (redis.RedisError, TypeError, ValueError):
            _LOG.warning("semantic_cache_redis_write_failed", bot_id=str(bot_id))

    async def embed_query(self, text: str, *, fail_open: bool = True) -> list[float] | None:
        if not self._settings.ai_semantic_cache_enabled:
            return None
        if not (self._settings.gemini_api_key or "").strip():
            return None
        http = await self._embed_client()
        return await gemini_embed_text(
            api_key=str(self._settings.gemini_api_key or ""),
            base_url=self._settings.gemini_api_base_url,
            model=str(self._settings.ai_semantic_cache_embedding_model),
            text=text,
            client=http,
            fail_open=fail_open,
        )

    async def lookup_exact(
        self,
        *,
        bot_id: uuid.UUID,
        conversation_state: str,
        normalized_message: str,
    ) -> str | None:
        if not self._settings.ai_exact_cache_enabled:
            return None
        key = _exact_cache_redis_key(self._settings, bot_id, conversation_state, normalized_message)
        try:
            r = await self._client()
            raw = await r.get(key)
        except redis.RedisError:
            _LOG.warning("exact_cache_redis_read_failed", bot_id=str(bot_id))
            return None
        if not raw:
            _LOG.debug(
                "exact_cache_miss",
                bot_id=str(bot_id),
                conversation_state=conversation_state[:64],
                query_chars=len(normalized_message),
            )
            return None
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            _LOG.debug(
                "exact_cache_miss",
                bot_id=str(bot_id),
                conversation_state=conversation_state[:64],
                query_chars=len(normalized_message),
                reason="corrupt_json",
            )
            return None
        if not isinstance(row, dict):
            _LOG.debug(
                "exact_cache_miss",
                bot_id=str(bot_id),
                conversation_state=conversation_state[:64],
                query_chars=len(normalized_message),
                reason="corrupt_type",
            )
            return None
        exp = float(row.get("exp", 0) or 0)
        if exp and time.time() > exp:
            _LOG.debug(
                "exact_cache_miss",
                bot_id=str(bot_id),
                conversation_state=conversation_state[:64],
                query_chars=len(normalized_message),
                reason="expired",
            )
            return None
        txt = row.get("r")
        if not isinstance(txt, str) or not txt.strip():
            _LOG.debug(
                "exact_cache_miss",
                bot_id=str(bot_id),
                conversation_state=conversation_state[:64],
                query_chars=len(normalized_message),
                reason="empty_value",
            )
            return None
        _LOG.info(
            "exact_cache_hit",
            bot_id=str(bot_id),
            conversation_state=conversation_state[:64],
            query_chars=len(normalized_message),
        )
        return txt.strip()

    async def remember_exact(
        self,
        *,
        bot_id: uuid.UUID,
        conversation_state: str,
        normalized_message: str,
        response_text: str,
    ) -> None:
        if not self._settings.ai_exact_cache_enabled:
            return
        key = _exact_cache_redis_key(self._settings, bot_id, conversation_state, normalized_message)
        ttl = int(self._settings.ai_exact_cache_ttl_seconds)
        exp = (time.time() + float(ttl)) if ttl > 0 else 0.0
        row = {"r": (response_text or "")[:8000], "exp": exp}
        try:
            r = await self._client()
            payload = json.dumps(row, separators=(",", ":"))
            if ttl > 0:
                await r.setex(key, ttl, payload)
            else:
                await r.set(key, payload)
            _LOG.debug(
                "exact_cache_store",
                bot_id=str(bot_id),
                conversation_state=conversation_state[:64],
                query_chars=len(normalized_message),
                ttl_seconds=ttl,
            )
        except (redis.RedisError, TypeError, ValueError):
            _LOG.warning("exact_cache_redis_write_failed", bot_id=str(bot_id))


__all__ = [
    "SemanticCompletionCache",
    "exact_cache_turn_allowed",
    "normalize_cache_message",
    "semantic_cache_turn_allowed",
]
