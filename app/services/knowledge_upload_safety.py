"""
Lightweight abuse signals for knowledge uploads (process-local).

* Sliding-window reject counts per ``owner_id:bot_id`` → structured log when a burst threshold is hit.
* Not a substitute for WAF or shared rate limits at the edge; complements per-route limits.
"""

from __future__ import annotations

import asyncio
import time
import uuid

from app.core.config import Settings
from app.core.logging import get_logger

_LOG = get_logger("knowledge_upload_safety")

_lock = asyncio.Lock()
_reject_timestamps: dict[str, list[float]] = {}


async def note_upload_validation_rejected(
    *,
    owner_id: uuid.UUID,
    bot_id: uuid.UUID,
    reason: str,
    settings: Settings,
) -> None:
    """
    Record a validation rejection; log once when the window fills (spam / misuse signal).

    ``reason`` should be a short stable code (e.g. ``invalid_extension``), not raw user input.
    """
    limit = settings.knowledge_upload_reject_burst_limit
    window = float(settings.knowledge_upload_reject_burst_window_seconds)
    if limit <= 1 or window <= 0:
        return

    key = f"{owner_id}:{bot_id}"
    now = time.monotonic()
    cutoff = now - window

    async with _lock:
        bucket = _reject_timestamps.setdefault(key, [])
        bucket[:] = [t for t in bucket if t > cutoff]
        bucket.append(now)
        if len(bucket) >= limit:
            _LOG.warning(
                "knowledge_upload_validation_burst",
                owner_id=str(owner_id),
                bot_id=str(bot_id),
                rejections_in_window=len(bucket),
                window_seconds=window,
                last_reason=reason[:120],
            )
