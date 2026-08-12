"""
Normalize Gemini / HTTP failures into stable ``error_code`` + safe messages.

Messages are intended for logs and API responses — never include API keys or raw secrets.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

# Stable codes for application handling (not Gemini enum strings).
TIMEOUT = "timeout"
CONNECTION_ERROR = "connection_error"
AUTH_FAILED = "auth_failed"
RATE_LIMITED = "rate_limited"
PROVIDER_ERROR = "provider_error"
INVALID_RESPONSE = "invalid_response"
INVALID_REQUEST = "invalid_request"
REQUEST_ERROR = "request_error"
UNEXPECTED_ERROR = "unexpected_error"

_MAX_MESSAGE_LEN = 512
# Google API keys often start with AIza; redact before surfacing provider error text.
_GOOGLE_KEY_LIKE = re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")


def _redact_secrets(msg: str) -> str:
    return _GOOGLE_KEY_LIKE.sub("[REDACTED]", msg)


def _truncate(msg: str) -> str:
    msg = msg.strip()
    if len(msg) <= _MAX_MESSAGE_LEN:
        return msg
    return msg[: _MAX_MESSAGE_LEN - 3] + "..."


def _google_error_from_body(body: str | None) -> tuple[str | None, str | None]:
    if not body:
        return None, None
    try:
        payload: Any = json.loads(body)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None, None
    if not isinstance(payload, dict):
        return None, None
    err = payload.get("error")
    if not isinstance(err, dict):
        return None, None
    status = err.get("status")
    message = err.get("message")
    code = str(status).strip() if status is not None else None
    msg = str(message).strip() if message is not None else None
    if not msg:
        return code, None
    return code, _redact_secrets(_truncate(msg))


def normalize_http_status_error(exc: httpx.HTTPStatusError) -> tuple[str, str]:
    status = exc.response.status_code
    g_code, g_msg = _google_error_from_body(exc.response.text)

    if status in (401, 403):
        return AUTH_FAILED, "AI provider rejected the API key or permissions."
    if status == 429:
        safe = _redact_secrets(g_msg) if g_msg else None
        return RATE_LIMITED, safe or "AI provider rate limit exceeded. Retry later."
    if status >= 500:
        safe = _redact_secrets(g_msg) if g_msg else None
        return PROVIDER_ERROR, safe or "The AI provider returned an internal error."
    if status == 400 and g_code:
        safe = _redact_secrets(g_msg) if g_msg else None
        return g_code, safe or "Invalid request to the AI provider."
    if g_msg:
        return g_code or f"http_{status}", _redact_secrets(g_msg)
    reason = (exc.response.reason_phrase or "").strip() or "request failed"
    return f"http_{status}", _redact_secrets(_truncate(reason))


def normalize_provider_exception(exc: BaseException) -> tuple[str, str]:
    """
    Map transport/API exceptions to ``(error_code, safe_message)``.

    Use for :class:`~app.ai_providers.base.AIProvider.normalize_error` and failed
    :class:`~app.ai_providers.types.NormalizedAIResult` payloads.
    """
    if isinstance(exc, httpx.TimeoutException):
        return TIMEOUT, "The AI provider request timed out."
    if isinstance(exc, httpx.ConnectError):
        return CONNECTION_ERROR, "Could not connect to the AI provider."
    if isinstance(exc, httpx.HTTPStatusError):
        return normalize_http_status_error(exc)
    if isinstance(exc, httpx.RequestError):
        return REQUEST_ERROR, "Network error while calling the AI provider."
    if isinstance(exc, json.JSONDecodeError):
        return INVALID_RESPONSE, "The AI provider returned invalid JSON."
    raw = str(exc) or type(exc).__name__
    return UNEXPECTED_ERROR, _redact_secrets(_truncate(raw))
