"""Construct limiters for ``app.state`` (Redis when URL set, else in-memory)."""

from __future__ import annotations

from fastapi import FastAPI

from app.core.config import Settings
from app.core.limiters.memory_sliding_window import InMemorySlidingWindowLimiter
from app.core.limiters.protocol import SlidingWindowLimiterPort
from app.core.limiters.redis_sliding_window import RedisSlidingWindowLimiter
from app.core.redis_client import get_redis_client


def attach_sliding_window_limiter(app: FastAPI, settings: Settings) -> SlidingWindowLimiterPort:
    """Create limiter and store on ``app.state.sliding_limiter``."""
    client = get_redis_client()
    if client is not None:
        lim: SlidingWindowLimiterPort = RedisSlidingWindowLimiter(
            client,
            key_prefix=settings.rate_limit_redis_key_prefix,
        )
    else:
        lim = InMemorySlidingWindowLimiter()
    app.state.sliding_limiter = lim
    return lim
