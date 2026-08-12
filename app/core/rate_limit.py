"""Backward-compatible import path; prefer :mod:`app.core.limiters`."""

from __future__ import annotations

from app.core.limiters.memory_sliding_window import InMemorySlidingWindowLimiter

__all__ = ["InMemorySlidingWindowLimiter"]
