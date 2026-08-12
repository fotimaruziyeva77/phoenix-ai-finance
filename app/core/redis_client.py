"""Shared async Redis client for rate limiting / abuse counters."""

from __future__ import annotations

from typing import TYPE_CHECKING

import redis.asyncio as redis

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.core.config import Settings

_LOG = get_logger(__name__)

_client: redis.Redis | None = None


async def init_redis_client(settings: Settings) -> redis.Redis | None:
    """
    Create a single :class:`redis.asyncio.Redis` for the process.

    Returns ``None`` when no URL is configured (callers use in-memory backends).
    """
    global _client
    url = settings.rate_limit_redis_url
    if not url or not str(url).strip():
        _LOG.info("redis_client_disabled", reason="rate_limit_redis_url_unset")
        _client = None
        return None
    _client = redis.from_url(
        str(url).strip(),
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=settings.rate_limit_redis_connect_timeout_seconds,
        socket_timeout=settings.rate_limit_redis_socket_timeout_seconds,
    )
    try:
        await _client.ping()
        _LOG.info("redis_client_connected", url_host=_safe_redis_log_hint(str(url)))
    except redis.RedisError as e:
        _LOG.warning(
            "redis_client_connect_failed",
            error_type=type(e).__name__,
            message=str(e),
            metric_event="rate_limit_redis_failure",
        )
        try:
            await _client.aclose()
        except redis.RedisError:
            pass
        _client = None
        return None
    return _client


def _safe_redis_log_hint(url: str) -> str:
    if "@" in url:
        return url.split("@", 1)[-1].split("/")[0]
    return "configured"


def get_redis_client() -> redis.Redis | None:
    return _client


async def close_redis_client() -> None:
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except redis.RedisError:
            pass
        _client = None
