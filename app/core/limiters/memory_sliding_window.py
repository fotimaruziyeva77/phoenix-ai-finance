"""In-process sliding window (single worker only)."""

from __future__ import annotations

import asyncio
import math
import time
import uuid

from app.core.limiters.outcome import RateLimitOutcome


class InMemorySlidingWindowLimiter:
    """
    In-memory limiter keyed by arbitrary string.

    Used when ``RATE_LIMIT_REDIS_URL`` is unset or for tests.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._hits: dict[str, list[float]] = {}

    async def consume(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: float,
    ) -> RateLimitOutcome:
        if limit <= 0:
            return RateLimitOutcome(allowed=True)
        now = time.monotonic()
        cutoff = now - window_seconds
        async with self._lock:
            bucket = self._hits.setdefault(key, [])
            bucket[:] = [t for t in bucket if t > cutoff]
            if len(bucket) >= limit:
                oldest = min(bucket)
                retry = max(0, int(math.ceil(oldest + window_seconds - now)))
                return RateLimitOutcome(allowed=False, retry_after_seconds=max(1, retry))
            bucket.append(now)
            return RateLimitOutcome(allowed=True)

    # Back-compat for older tests / call sites
    async def allow(self, key: str, *, limit: int, window_seconds: float) -> bool:
        out = await self.consume(key, limit=limit, window_seconds=window_seconds)
        return out.allowed
