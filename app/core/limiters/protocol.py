from __future__ import annotations

from typing import Protocol

from app.core.limiters.outcome import RateLimitOutcome


class SlidingWindowLimiterPort(Protocol):
    """
    Sliding-window counter shared across workers when backed by Redis.

    Keys are opaque UTF-8 strings built by callers (IP, user_id, widget digest, etc.).
    """

    async def consume(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: float,
    ) -> RateLimitOutcome:
        """
        Record one hit if under ``limit`` events in the last ``window_seconds``.

        When not allowed, ``retry_after_seconds`` hints when the oldest event exits the window.
        """
        ...
