"""
HTTP request logging context: correlation IDs, safe path hints, and route templates.

Central place for field names so JSON logs stay consistent across middleware, auth, and services.

**Example JSON line** (``APP_LOG_JSON=true``) after a completed authenticated API call::

    {
      "timestamp": "2026-04-08T12:00:00.000000Z",
      "level": "info",
      "service": "api",
      "environment": "production",
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "…",
      "bot_id": "…",
      "channel": "web_widget",
      "http_method": "POST",
      "http_path": "/api/v1/public/widget/…/chat",
      "http_route": "/api/v1/public/widget/{public_widget_key}/chat",
      "http_status": 200,
      "duration_ms": 42.5,
      "event": "http_request",
      "http_event": "completed"
    }

* Never put tokens, webhook secrets, message bodies, or raw widget keys in these fields.
* ``bot_id`` / ``channel`` from path hints are best-effort; handlers may bind richer context.
"""

from __future__ import annotations

import re
import uuid
from typing import Any
from uuid import UUID

import structlog
from starlette.requests import Request

from app.lib.chat_channels import CONVERSATION_CHANNEL_TELEGRAM, CONVERSATION_CHANNEL_WEB_WIDGET

HEADER_CORRELATION_ID = "x-correlation-id"
HEADER_REQUEST_ID = "x-request-id"
# W3C Trace Context (https://www.w3.org/TR/trace-context/); bind trace id into logs for gateway ↔ API correlation.
HEADER_TRACEPARENT = "traceparent"


def w3c_trace_id_from_traceparent(header_value: str | None) -> str | None:
    """
    Extract the 32-char hex trace id from a ``traceparent`` header value.

    Does not parse ``tracestate``; safe to call on untrusted input (returns None on bad shape).
    """
    raw = (header_value or "").strip()
    if not raw:
        return None
    parts = raw.split("-")
    if len(parts) < 2:
        return None
    tid = parts[1].strip().lower()
    if len(tid) != 32 or any(c not in "0123456789abcdef" for c in tid):
        return None
    return tid

# UUID immediately after /api/v1/bots/ or /api/v1/public/telegram/.../webhook
_BOT_SEGMENT_RE = re.compile(
    r"/api/v1/bots/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(?:/|$)"
)
_TELEGRAM_WEBHOOK_RE = re.compile(
    r"/api/v1/public/telegram/"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
    r"/webhook(?:/|$)"
)


def parse_request_and_correlation_ids(request: Request) -> tuple[str, str]:
    """
    Return ``(request_id, correlation_id)``.

    ``request_id`` comes from ``X-Request-ID`` or a new UUID.
    ``correlation_id`` comes from ``X-Correlation-ID`` when non-empty, else equals ``request_id``.
    """
    raw_rid = request.headers.get(HEADER_REQUEST_ID)
    request_id = (raw_rid or "").strip() or str(uuid.uuid4())

    raw_cid = request.headers.get(HEADER_CORRELATION_ID)
    cid = (raw_cid or "").strip()
    correlation_id = cid if cid else request_id

    return request_id, correlation_id


def infer_path_log_context(http_path: str) -> dict[str, str]:
    """
    Derive safe correlators from the URL path only (no bodies, no secrets).

    Sets ``bot_id`` for owner bot routes and Telegram webhook paths; ``channel`` for public ingress.
    """
    out: dict[str, str] = {}
    path = (http_path or "").strip() or "/"

    if "/api/v1/public/widget/" in path:
        out["channel"] = CONVERSATION_CHANNEL_WEB_WIDGET

    m_tg = _TELEGRAM_WEBHOOK_RE.search(path)
    if m_tg:
        out["channel"] = CONVERSATION_CHANNEL_TELEGRAM
        out["bot_id"] = m_tg.group(1).lower()
    else:
        m_bot = _BOT_SEGMENT_RE.search(path)
        if m_bot:
            out["bot_id"] = m_bot.group(1).lower()

    return out


def matched_route_template(request: Request) -> str | None:
    """OpenAPI/FastAPI route pattern (e.g. ``/api/v1/bots/{bot_id}``) when routing has run."""
    route = request.scope.get("route")
    if route is None:
        return None
    path = getattr(route, "path", None)
    if path is None:
        return None
    s = str(path).strip()
    return s or None


def bind_log_contextvars(**kwargs: Any) -> None:
    """Bind only non-None scalar values into structlog contextvars."""
    merged = {k: v for k, v in kwargs.items() if v is not None and v != ""}
    if merged:
        structlog.contextvars.bind_contextvars(**merged)


def bind_user_id_for_request(user_id: UUID | str) -> None:
    """Call after authenticated user resolution (JWT path); id only, never email or token."""
    bind_log_contextvars(user_id=str(user_id))


def bind_bot_and_channel(*, bot_id: UUID | str | None = None, channel: str | None = None) -> None:
    """Optional service-layer hints (e.g. conversation channel overrides path inference)."""
    kwargs: dict[str, Any] = {}
    if bot_id is not None:
        kwargs["bot_id"] = str(bot_id)
    if channel is not None and str(channel).strip():
        kwargs["channel"] = str(channel).strip()[:64]
    bind_log_contextvars(**kwargs)
