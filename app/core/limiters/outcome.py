from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RateLimitOutcome:
    """Result of a single sliding-window consumption attempt."""

    allowed: bool
    """Seconds clients may wait before retry; set when ``allowed`` is False."""
    retry_after_seconds: int | None = None
