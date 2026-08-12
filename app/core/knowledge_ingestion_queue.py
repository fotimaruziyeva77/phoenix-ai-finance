"""
Redis list queue for knowledge PDF ingestion jobs (file_id only).

API enqueues after successful upload; workers BRPOP and run
:class:`~app.services.knowledge_file_processing_service.KnowledgeFileProcessingService`.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

import redis.asyncio as redis

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.core.config import Settings

_LOG = get_logger("knowledge_ingestion_queue")

_redis_client: redis.Redis | None = None
_redis_url_bound: str | None = None


def reset_knowledge_ingestion_redis_client_for_tests() -> None:
    """Drop cached async Redis client (pytest isolation)."""
    global _redis_client, _redis_url_bound
    _redis_client = None
    _redis_url_bound = None


async def _shared_async_redis(url: str) -> redis.Redis:
    global _redis_client, _redis_url_bound
    if _redis_client is not None and _redis_url_bound == url:
        return _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
    _redis_url_bound = url
    _redis_client = redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=5.0,
        socket_timeout=60.0,
    )
    return _redis_client


class RedisKnowledgeIngestionQueue:
    """LPUSH / BRPOP queue of JSON payloads ``{\"file_id\": \"<uuid>\"}``."""

    def __init__(self, client: redis.Redis, queue_key: str) -> None:
        self._r = client
        self._key = queue_key

    async def enqueue(self, file_id: uuid.UUID) -> None:
        payload = json.dumps({"file_id": str(file_id)})
        await self._r.lpush(self._key, payload)
        _LOG.info(
            "knowledge_ingestion_enqueued",
            file_id=str(file_id),
            queue_key=self._key,
        )

    async def blocking_pop_next(self, *, timeout_seconds: int) -> uuid.UUID | None:
        out = await self._r.brpop(self._key, timeout=timeout_seconds)
        if out is None:
            return None
        _, raw = out
        try:
            data = json.loads(raw)
            fid = uuid.UUID(str(data["file_id"]))
        except (KeyError, TypeError, ValueError) as exc:
            _LOG.warning(
                "knowledge_ingestion_queue_bad_payload",
                raw_preview=(raw[:200] if isinstance(raw, str) else repr(raw))[:200],
                error=str(exc),
            )
            return None
        return fid

    async def non_blocking_pop_next(self) -> uuid.UUID | None:
        raw = await self._r.rpop(self._key)
        if raw is None:
            return None
        try:
            data = json.loads(raw)
            return uuid.UUID(str(data["file_id"]))
        except (KeyError, TypeError, ValueError) as exc:
            _LOG.warning(
                "knowledge_ingestion_queue_bad_payload",
                raw_preview=(raw[:200] if isinstance(raw, str) else repr(raw))[:200],
                error=str(exc),
            )
            return None

    async def queued_count(self) -> int:
        return int(await self._r.llen(self._key))


async def knowledge_ingestion_queue_from_settings(settings: Settings) -> RedisKnowledgeIngestionQueue | None:
    if not settings.knowledge_ingestion_enabled:
        return None
    url = settings.knowledge_ingestion_redis_url_effective
    if not url:
        return None
    client = await _shared_async_redis(url)
    return RedisKnowledgeIngestionQueue(client, settings.knowledge_ingestion_queue_key)


async def schedule_knowledge_file_ingestion(settings: Settings, file_id: uuid.UUID) -> bool:
    """
    Enqueue a file for background processing.

    Returns True if a message was pushed; False if ingestion is disabled or Redis is not configured.
    """
    try:
        queue = await knowledge_ingestion_queue_from_settings(settings)
        if queue is None:
            _LOG.warning(
                "knowledge_ingestion_not_scheduled",
                file_id=str(file_id),
                reason="queue_unavailable",
                ingestion_enabled=settings.knowledge_ingestion_enabled,
                has_redis_url=bool(settings.knowledge_ingestion_redis_url_effective),
            )
            return False
        await queue.enqueue(file_id)
        return True
    except Exception as exc:  # noqa: BLE001 — never fail upload on enqueue errors
        _LOG.exception(
            "knowledge_ingestion_enqueue_failed",
            file_id=str(file_id),
            error=str(exc),
        )
        return False
