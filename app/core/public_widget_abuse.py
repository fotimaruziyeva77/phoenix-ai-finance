"""
Anti-abuse for the public web widget (Redis-backed when configured, else in-process).

**Strategy**
    * **Coarse cap** — per-IP + widget key limit in :mod:`app.api.deps` (first line against flooding).
    * **Session burst** — sliding window per visitor session (opaque key) or, before a key exists,
      per IP for that widget (weaker, but unavoidable for the first message).
    * **Identical text burst** — many copies of the same normalized message inside a long window.
    * **Consecutive duplicates** — rapid repeats with no other text in between (paste / script spam).
    * **Length cap** — stricter than the JSON schema maximum to reduce paste attacks without
      affecting typical chats.

**Client-facing behavior**
    * Throttle / soft-block rules return **HTTP 429** with a single generic message (no rule names).
    * Oversize messages return **HTTP 400** with a short, safe explanation.

**Logging**
    * Throttle / abuse blocks emit ``widget_throttled`` via
      :mod:`app.core.public_widget_channel_events` (digest only, no message body, no visitor material, no IP).

Deterministic: fixed thresholds from :class:`~app.core.config.Settings`, no randomness, no ML.
With ``APP_RATE_LIMIT_REDIS_URL``, session burst and identical-window counts are shared across workers;
consecutive-identical streaks use Redis when the shared client is available.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import TYPE_CHECKING

import redis.asyncio as redis
from fastapi import HTTPException, Request, status

from app.core.limiters.protocol import SlidingWindowLimiterPort
from app.core.logging import get_logger
from app.core.public_widget_channel_events import (
    THROTTLE_ABUSE_CONSECUTIVE_IDENTICAL,
    THROTTLE_ABUSE_IDENTICAL_BURST,
    THROTTLE_ABUSE_MESSAGE_TOO_LONG,
    THROTTLE_ABUSE_SESSION_BURST,
    WIDGET_THROTTLED,
    emit_public_widget_channel_event,
)
from app.core.request_client import client_ip
from app.core.widget_abuse_redis import RedisWidgetStreakTracker

if TYPE_CHECKING:
    from app.core.config import Settings

_LOG = get_logger(__name__)

_ABUSE_REASON_TO_THROTTLE_KIND = {
    "message_too_long": THROTTLE_ABUSE_MESSAGE_TOO_LONG,
    "session_burst": THROTTLE_ABUSE_SESSION_BURST,
    "identical_message_burst": THROTTLE_ABUSE_IDENTICAL_BURST,
    "consecutive_identical": THROTTLE_ABUSE_CONSECUTIVE_IDENTICAL,
}

# --- Identical-message windows (in-process fallback when Redis streak tracker is unset) ---
_identical_lock = asyncio.Lock()
_identical_events: dict[str, list[float]] = {}

# --- Consecutive duplicate streak (in-process fallback) ---
_streak_lock = asyncio.Lock()
_streak_state: dict[str, tuple[str, int]] = {}

_MAX_TRACKED_KEYS = 50_000


def _retry_headers(retry_after_seconds: int | None) -> dict[str, str]:
    if retry_after_seconds is None or retry_after_seconds <= 0:
        return {"Retry-After": "60"}
    return {"Retry-After": str(max(1, int(retry_after_seconds)))}


def widget_key_digest(public_widget_key: str) -> str:
    return hashlib.sha256(public_widget_key.strip().encode("utf-8")).hexdigest()[:16]


def _message_fingerprint(text: str) -> str:
    normalized = " ".join((text or "").split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _abuse_session_bucket(*, visitor_session_key: str | None, ip: str) -> str:
    raw = (visitor_session_key or "").strip()
    if len(raw) >= 16:
        return "s:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return "i:" + ip


def _maybe_trim_map(store: dict, cap: int = _MAX_TRACKED_KEYS) -> None:
    if len(store) > cap:
        store.clear()


def _redis_abuse_fail_open(settings: Settings) -> bool:
    return bool(settings.rate_limit_public_fail_open_on_redis_error)


async def enforce_public_widget_chat_turn(
    *,
    request: Request,
    settings: Settings,
    public_widget_key: str,
    message_text: str,
    visitor_session_key: str | None,
    limiter: SlidingWindowLimiterPort,
    streak_tracker: RedisWidgetStreakTracker | None = None,
) -> None:
    """
    Apply session / content heuristics for one chat POST.

    Assumes coarse IP+widget limiting already ran. Raises :class:`fastapi.HTTPException` on violation.
    """
    if not settings.rate_limiting_enabled or not settings.public_widget_abuse_enabled:
        return

    digest = widget_key_digest(public_widget_key)
    ip = client_ip(request, trust_forwarded_for=settings.trust_forwarded_for) or "unknown"
    bucket = _abuse_session_bucket(visitor_session_key=visitor_session_key, ip=ip)

    max_chars = int(settings.public_widget_abuse_max_message_chars)
    if max_chars > 0 and len(message_text) > max_chars:
        emit_public_widget_channel_event(
            event=WIDGET_THROTTLED,
            level="warning",
            widget_key_digest=digest,
            throttle_kind=_ABUSE_REASON_TO_THROTTLE_KIND["message_too_long"],
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message is too long for this chat. Please shorten your text.",
        )

    fp = _message_fingerprint(message_text)

    burst_limit = int(settings.public_widget_abuse_session_burst_per_minute)
    if burst_limit > 0:
        try:
            bout = await limiter.consume(
                f"pub_wg_sess_burst:{digest}:{bucket}",
                limit=burst_limit,
                window_seconds=60.0,
            )
        except redis.RedisError:
            _LOG.warning(
                "widget_abuse_redis_degraded",
                abuse_check="session_burst",
                policy="fail_open" if _redis_abuse_fail_open(settings) else "fail_closed",
                metric_event="widget_abuse_redis_failure",
            )
            if not _redis_abuse_fail_open(settings):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service temporarily unavailable. Please try again shortly.",
                )
        else:
            if not bout.allowed:
                _LOG.info(
                    "public_widget_abuse_blocked",
                    abuse_kind="session_burst",
                    widget_key_digest=digest,
                    metric_event="widget_abuse_threshold",
                )
                emit_public_widget_channel_event(
                    event=WIDGET_THROTTLED,
                    level="warning",
                    widget_key_digest=digest,
                    throttle_kind=_ABUSE_REASON_TO_THROTTLE_KIND["session_burst"],
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many messages. Please try again shortly.",
                    headers=_retry_headers(bout.retry_after_seconds),
                )

    ident_limit = int(settings.public_widget_abuse_identical_total_per_window)
    ident_window = float(settings.public_widget_abuse_identical_window_seconds)
    if ident_limit > 0 and ident_window > 0:
        ik = f"idup:{digest}:{bucket}:{fp}"
        if streak_tracker is not None:
            try:
                iout = await limiter.consume(ik, limit=ident_limit, window_seconds=ident_window)
            except redis.RedisError:
                _LOG.warning(
                    "widget_abuse_redis_degraded",
                    abuse_check="identical_message_burst",
                    policy="fail_open" if _redis_abuse_fail_open(settings) else "fail_closed",
                    metric_event="widget_abuse_redis_failure",
                )
                if not _redis_abuse_fail_open(settings):
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Service temporarily unavailable. Please try again shortly.",
                    )
            else:
                if not iout.allowed:
                    _LOG.info(
                        "public_widget_abuse_blocked",
                        abuse_kind="identical_message_burst",
                        widget_key_digest=digest,
                        metric_event="widget_abuse_threshold",
                    )
                    emit_public_widget_channel_event(
                        event=WIDGET_THROTTLED,
                        level="warning",
                        widget_key_digest=digest,
                        throttle_kind=_ABUSE_REASON_TO_THROTTLE_KIND["identical_message_burst"],
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many messages. Please try again shortly.",
                        headers=_retry_headers(iout.retry_after_seconds),
                    )
        else:
            now = time.monotonic()
            async with _identical_lock:
                _maybe_trim_map(_identical_events)
                series = _identical_events.setdefault(ik, [])
                series[:] = [t for t in series if now - t < ident_window]
                series.append(now)
                if len(series) >= ident_limit:
                    _LOG.info(
                        "public_widget_abuse_blocked",
                        abuse_kind="identical_message_burst",
                        widget_key_digest=digest,
                        metric_event="widget_abuse_threshold",
                    )
                    emit_public_widget_channel_event(
                        event=WIDGET_THROTTLED,
                        level="warning",
                        widget_key_digest=digest,
                        throttle_kind=_ABUSE_REASON_TO_THROTTLE_KIND["identical_message_burst"],
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many messages. Please try again shortly.",
                        headers=_retry_headers(60),
                    )

    cons_limit = int(settings.public_widget_abuse_max_consecutive_identical)
    if cons_limit > 0:
        sk = f"cst:{digest}:{bucket}"
        if streak_tracker is not None:
            try:
                cout = await streak_tracker.check_and_record(
                    sk,
                    fp,
                    limit=cons_limit,
                    ttl_seconds=3600,
                )
            except redis.RedisError:
                _LOG.warning(
                    "widget_abuse_redis_degraded",
                    abuse_check="consecutive_identical",
                    policy="fail_open" if _redis_abuse_fail_open(settings) else "fail_closed",
                    metric_event="widget_abuse_redis_failure",
                )
                if not _redis_abuse_fail_open(settings):
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Service temporarily unavailable. Please try again shortly.",
                    )
            else:
                if not cout.allowed:
                    _LOG.info(
                        "public_widget_abuse_blocked",
                        abuse_kind="consecutive_identical",
                        widget_key_digest=digest,
                        metric_event="widget_abuse_threshold",
                    )
                    emit_public_widget_channel_event(
                        event=WIDGET_THROTTLED,
                        level="warning",
                        widget_key_digest=digest,
                        throttle_kind=_ABUSE_REASON_TO_THROTTLE_KIND["consecutive_identical"],
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many messages. Please try again shortly.",
                        headers=_retry_headers(cout.retry_after_seconds),
                    )
        else:
            async with _streak_lock:
                _maybe_trim_map(_streak_state)
                prev_fp, streak = _streak_state.get(sk, ("", 0))
                if fp == prev_fp:
                    streak += 1
                else:
                    streak = 1
                _streak_state[sk] = (fp, streak)
                if streak >= cons_limit:
                    _LOG.info(
                        "public_widget_abuse_blocked",
                        abuse_kind="consecutive_identical",
                        widget_key_digest=digest,
                        metric_event="widget_abuse_threshold",
                    )
                    emit_public_widget_channel_event(
                        event=WIDGET_THROTTLED,
                        level="warning",
                        widget_key_digest=digest,
                        throttle_kind=_ABUSE_REASON_TO_THROTTLE_KIND["consecutive_identical"],
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many messages. Please try again shortly.",
                        headers=_retry_headers(60),
                    )


def reset_public_widget_abuse_memory_for_tests() -> None:
    """Clear process-local abuse counters (pytest only)."""
    _identical_events.clear()
    _streak_state.clear()
