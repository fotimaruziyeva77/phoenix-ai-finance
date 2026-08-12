"""
Optional production error tracking (Sentry-compatible).

* **Off by default locally:** no ``SENTRY_DSN`` / ``APP_SENTRY_DSN`` → all calls are no-ops.
* **No hard dependency:** if ``sentry-sdk`` is not installed, initialization is skipped safely.
* **Manual capture only:** framework auto-integrations are disabled to avoid duplicate reports and
  accidental request body/header capture; we attach a minimal safe HTTP context ourselves.

**What gets reported (high level)**

* Unhandled exceptions (500 path through :mod:`app.core.exception_handlers`).
* HTTP-mapped domain errors with status **≥ 500** (auth config, Telegram, widget, knowledge API, AI HTTP errors).
* AI provider turn failures (excluding routine ``rate_limited`` noise) as structured messages.
* Telegram inbound pipeline **unhandled** exceptions.
* Knowledge **PDF processing** failures (storage/read/extract/chunk persistence).

**What is never sent intentionally**

* Passwords, tokens, ``Authorization`` headers, cookies, raw JWTs (Sentry ``before_send`` scrubs
  common keys; we do not attach request bodies).

Install in production: ``pip install sentry-sdk`` (see ``requirements.txt``).
"""

from __future__ import annotations

import re
from typing import Any, Mapping
from urllib.parse import urlsplit

from starlette.requests import Request

from app.core.config import Settings
from app.core.logging import get_logger

_LOG = get_logger(__name__)

_initialized: bool = False

_SENSITIVE_KEY_RE = re.compile(
    r"(password|secret|token|authorization|cookie|apikey|api_key|goog-api-key|refresh|credential)",
    re.I,
)


def error_tracking_is_active(settings: Settings | None = None) -> bool:
    s = settings
    if s is None:
        from app.core.config import get_settings

        s = get_settings()
    if not s.error_tracking_enabled:
        return False
    dsn = (s.error_tracking_sentry_dsn or "").strip()
    return bool(dsn)


def _scrub_value(obj: Any, depth: int = 0) -> Any:
    if depth > 8:
        return "[depth_limit]"
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            ks = str(k)
            if _SENSITIVE_KEY_RE.search(ks):
                out[ks] = "[redacted]"
            else:
                out[ks] = _scrub_value(v, depth + 1)
        return out
    if isinstance(obj, list):
        return [_scrub_value(x, depth + 1) for x in obj[:50]]
    return obj


def _before_send_sentry(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    try:
        req = event.get("request")
        if isinstance(req, dict):
            req.pop("cookies", None)
            req.pop("headers", None)
            req.pop("data", None)
            req.pop("query_string", None)
            url = req.get("url")
            if isinstance(url, str) and "?" in url:
                req["url"] = urlsplit(url)._replace(query="").geturl()
            event["request"] = req
        event = _scrub_value(event)
    except Exception:
        return event
    return event


def _safe_request_context(request: Request | None) -> dict[str, Any]:
    if request is None:
        return {}
    return {
        "method": request.method,
        "path": request.url.path,
        "request_id": getattr(request.state, "request_id", None),
        "correlation_id": getattr(request.state, "correlation_id", None),
        "w3c_trace_id": getattr(request.state, "w3c_trace_id", None),
    }


def init_error_tracking(settings: Settings) -> None:
    """Call once at process startup (e.g. FastAPI lifespan). Safe to call multiple times."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    if not error_tracking_is_active(settings):
        return

    try:
        import sentry_sdk
    except ImportError:
        _LOG.warning(
            "error_tracking_sentry_sdk_missing",
            hint="pip install sentry-sdk to enable error_tracking_sentry_dsn",
        )
        return

    dsn = (settings.error_tracking_sentry_dsn or "").strip()
    environment = (settings.environment or "local").strip()[:64]
    release = (settings.error_tracking_release or settings.app_version or "").strip() or None

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        send_default_pii=False,
        traces_sample_rate=float(settings.error_tracking_traces_sample_rate),
        default_integrations=False,
        integrations=[],
        before_send=_before_send_sentry,
    )
    _LOG.info("error_tracking_initialized", backend="sentry", environment=environment)


def shutdown_error_tracking(*, timeout: float = 2.0) -> None:
    try:
        import sentry_sdk

        sentry_sdk.flush(timeout=timeout)
    except Exception:
        pass


def capture_exception(
    exc: BaseException,
    *,
    domain: str,
    request: Request | None = None,
    tags: Mapping[str, str | int | float | bool] | None = None,
) -> None:
    if not error_tracking_is_active():
        return
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            scope.set_tag("domain", (domain or "unknown")[:64])
            if tags:
                for k, v in tags.items():
                    scope.set_tag(str(k)[:32], str(v)[:200])
            ctx = _safe_request_context(request)
            if ctx:
                scope.set_context("http_safe", ctx)
            sentry_sdk.capture_exception(exc)
    except Exception:
        pass


def capture_message(
    message: str,
    *,
    domain: str,
    level: str = "error",
    request: Request | None = None,
    tags: Mapping[str, str | int | float | bool] | None = None,
    fingerprint: list[str] | None = None,
) -> None:
    if not error_tracking_is_active():
        return
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            scope.set_tag("domain", (domain or "unknown")[:64])
            if tags:
                for k, v in tags.items():
                    scope.set_tag(str(k)[:32], str(v)[:200])
            ctx = _safe_request_context(request)
            if ctx:
                scope.set_context("http_safe", ctx)
            if fingerprint:
                scope.fingerprint = [str(x)[:120] for x in fingerprint[:12]]
            sentry_sdk.capture_message((message or "")[:8192], level=level)
    except Exception:
        pass


def report_ai_provider_turn_failure(
    *,
    success: bool,
    provider_name: str,
    provider_error_code: str | None,
    ai_category: str | None,
    conversation_id: str,
    bot_id: str,
    channel: str | None = None,
) -> None:
    """Structured AI failures for monitoring (skips high-volume benign codes)."""
    if success or not error_tracking_is_active():
        return
    ec = (provider_error_code or "").strip().lower()
    if ec in {"rate_limited"}:
        return
    tags: dict[str, str] = {
        "bot_id": str(bot_id),
        "conversation_id": str(conversation_id),
        "provider": (provider_name or "")[:64],
        "provider_error_code": ec[:96] if ec else "",
        "ai_category": (ai_category or "")[:64],
    }
    if channel:
        tags["channel"] = str(channel)[:64]
    capture_message(
        f"ai_provider_failure:{provider_name}:{ec or ai_category or 'unknown'}",
        domain="ai_provider",
        level="warning" if ec in {"invalid_response", "empty_completion"} else "error",
        tags=tags,
        fingerprint=["ai_provider", provider_name or "", ec or "", ai_category or ""],
    )


def report_server_mapped_error(
    *,
    request: Request | None,
    domain: str,
    status_code: int,
    code: str,
    exc: BaseException | None = None,
) -> None:
    """Report mapped HTTP errors that indicate server/upstream failure (5xx)."""
    if status_code < 500 or not error_tracking_is_active():
        return
    tags = {"http_status": str(status_code), "error_code": (code or "")[:128]}
    if exc is not None:
        capture_exception(exc, domain=domain, request=request, tags=tags)
    else:
        capture_message(
            f"{domain}:{code}",
            domain=domain,
            level="error",
            request=request,
            tags=tags,
            fingerprint=[domain, str(status_code), code],
        )
