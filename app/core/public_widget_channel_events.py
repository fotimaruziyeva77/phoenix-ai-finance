"""
Structured, privacy-safe hooks for public web-widget channel observability.

Logs are suitable for future dashboard analytics (Sprint 11/12): one JSON line per event with
stable field names. Never log raw ``public_widget_key``, visitor session secrets, message text,
owner PII, or model payloads.

**Events** (``widget_event`` field — not ``event``, reserved by structlog):

* ``widget_bootstrap_loaded`` — bootstrap succeeded after origin + enabled checks.
* ``widget_message_received`` — chat request passed gating; conversation bound; before AI call.
* ``widget_message_answered`` — assistant reply returned to client.
* ``widget_throttled`` — rate limit or abuse rule blocked the request.
* ``widget_error`` — widget/bootstrap/session/chat domain error response (code only).

Correlators: ``bot_id``, ``widget_config_id``, ``widget_key_digest`` (SHA-256 prefix),
``conversation_id``, ``visitor_session_digest`` (hash prefix; only when session key is long enough).
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Literal
from uuid import UUID

from app.core.logging import get_logger

_LOG = get_logger("public_widget_channel")

CHANNEL_WEB_WIDGET = "web_widget"

# Event name constants (for callers and log consumers).
WIDGET_BOOTSTRAP_LOADED = "widget_bootstrap_loaded"
WIDGET_MESSAGE_RECEIVED = "widget_message_received"
WIDGET_MESSAGE_ANSWERED = "widget_message_answered"
WIDGET_THROTTLED = "widget_throttled"
WIDGET_ERROR = "widget_error"

# throttle_kind values (stable enum strings for dashboards).
THROTTLE_RATE_LIMIT_CHAT = "rate_limit_chat"
THROTTLE_RATE_LIMIT_BOOTSTRAP = "rate_limit_bootstrap"
THROTTLE_ABUSE_MESSAGE_TOO_LONG = "abuse_message_too_long"
THROTTLE_ABUSE_SESSION_BURST = "abuse_session_burst"
THROTTLE_ABUSE_IDENTICAL_BURST = "abuse_identical_message_burst"
THROTTLE_ABUSE_CONSECUTIVE_IDENTICAL = "abuse_consecutive_identical"

_PATH_KEY_RE = re.compile(r"/api/v1/public/widget/([^/]+)/(?:bootstrap|chat)")


def is_public_widget_chat_path(path: str) -> bool:
    """True when ``path`` is the public widget chat route (for error/analytics routing)."""
    if _PATH_KEY_RE.search(path) is None:
        return False
    return path.rstrip("/").endswith("/chat")


def public_widget_key_digest_from_path(path: str) -> str | None:
    """Extract public key from bootstrap/chat path and return short digest; never log the raw key."""
    m = _PATH_KEY_RE.search(path)
    if not m:
        return None
    raw = m.group(1).strip()
    if not raw:
        return None
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def visitor_session_digest(visitor_session_key: str | None) -> str | None:
    """
    Non-reversible correlator for visitor session (same cut as abuse bucket when key is present).

    Short / empty keys are omitted so we do not log low-entropy client data.
    """
    raw = (visitor_session_key or "").strip()
    if len(raw) < 16:
        return None
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def emit_public_widget_channel_event(
    *,
    event: str,
    level: Literal["info", "warning"] = "info",
    channel: str = CHANNEL_WEB_WIDGET,
    bot_id: UUID | str | None = None,
    widget_config_id: UUID | str | None = None,
    widget_key_digest: str | None = None,
    conversation_id: UUID | str | None = None,
    visitor_session_digest: str | None = None,
    throttle_kind: str | None = None,
    error_code: str | None = None,
    http_status: int | None = None,
    latency_ms: int | None = None,
    inbound_chars: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit one structured log line. Unknown or empty fields are omitted."""
    payload: dict[str, Any] = {
        "channel": channel,
        "widget_event": event,
    }
    if bot_id is not None:
        payload["bot_id"] = str(bot_id)
    if widget_config_id is not None:
        payload["widget_config_id"] = str(widget_config_id)
    if widget_key_digest:
        payload["widget_key_digest"] = widget_key_digest
    if conversation_id is not None:
        payload["conversation_id"] = str(conversation_id)
    if visitor_session_digest:
        payload["visitor_session_digest"] = visitor_session_digest
    if throttle_kind:
        payload["throttle_kind"] = throttle_kind
    if error_code:
        payload["error_code"] = error_code
    if http_status is not None:
        payload["http_status"] = http_status
    if latency_ms is not None:
        payload["latency_ms"] = latency_ms
    if inbound_chars is not None:
        payload["inbound_chars"] = inbound_chars
    if extra:
        for k, v in extra.items():
            if v is not None:
                payload[k] = v

    if level == "warning":
        _LOG.warning("public_widget_channel_event", **payload)
    else:
        _LOG.info("public_widget_channel_event", **payload)
