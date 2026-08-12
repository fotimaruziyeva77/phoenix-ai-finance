import time
from typing import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.request_log_context import (
    HEADER_TRACEPARENT,
    infer_path_log_context,
    matched_route_template,
    parse_request_and_correlation_ids,
    w3c_trace_id_from_traceparent,
)

_LOG = get_logger("http")


def _state_str(request: Request, name: str) -> str | None:
    raw = getattr(request.state, name, None)
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request / correlation IDs + compact structured access logging.

    * Accepts ``X-Request-ID`` and ``X-Correlation-ID``; echoes both on the response.
    * Binds ``request_id``, ``correlation_id``, and safe path hints (``bot_id``, ``channel``) into
      structlog contextvars for the lifetime of the request.
    * Does not log bodies, cookies, or ``Authorization`` (avoid secret leakage).
    * Emits a single INFO line per successful request; ``request_started`` is DEBUG-only to limit noise.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        settings = get_settings()
        request_id, correlation_id = parse_request_and_correlation_ids(request)
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        trace_id = w3c_trace_id_from_traceparent(request.headers.get(HEADER_TRACEPARENT))
        if trace_id:
            request.state.w3c_trace_id = trace_id

        path = request.url.path
        method = request.method
        client_host = request.client.host if request.client else None
        path_ctx = infer_path_log_context(path)

        structlog.contextvars.clear_contextvars()
        bind_kw: dict[str, object] = {
            "service": settings.service_name,
            "environment": str(settings.environment).strip()[:64],
            "request_id": request_id,
            "correlation_id": correlation_id,
            **path_ctx,
        }
        if trace_id:
            bind_kw["w3c_trace_id"] = trace_id
        structlog.contextvars.bind_contextvars(**bind_kw)

        extra_dbg: dict[str, object] = {}
        if settings.log_request_body and method in ("POST", "PUT", "PATCH"):
            extra_dbg["note"] = "body_logging_not_enabled_use_audit_pipeline"

        _LOG.debug(
            "http_request",
            http_event="started",
            http_method=method,
            http_path=path,
            client_host=client_host,
            **extra_dbg,
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 3)
            route_tpl = matched_route_template(request)
            uid = _state_str(request, "log_user_id")
            bid = _state_str(request, "log_bot_id") or path_ctx.get("bot_id")
            ch = _state_str(request, "log_channel") or path_ctx.get("channel")
            fail_fields: dict[str, object] = {
                "request_id": request_id,
                "correlation_id": correlation_id,
                "http_method": method,
                "http_path": path,
                "http_route": route_tpl,
                "user_id": uid,
                "bot_id": bid,
                "channel": ch,
                "duration_ms": duration_ms,
            }
            if trace_id:
                fail_fields["w3c_trace_id"] = trace_id
            _LOG.warning("http_request", http_event="failed", **fail_fields)
            structlog.contextvars.clear_contextvars()
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        route_tpl = matched_route_template(request)
        uid = _state_str(request, "log_user_id")
        bid = _state_str(request, "log_bot_id") or path_ctx.get("bot_id")
        ch = _state_str(request, "log_channel") or path_ctx.get("channel")

        log_fn = _LOG.info
        if response.status_code >= 500:
            log_fn = _LOG.error
        elif response.status_code >= 400:
            log_fn = _LOG.warning

        completed_fields: dict[str, object] = {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "http_method": method,
            "http_path": path,
            "http_route": route_tpl,
            "http_status": response.status_code,
            "duration_ms": duration_ms,
            "user_id": uid,
            "bot_id": bid,
            "channel": ch,
        }
        if trace_id:
            completed_fields["w3c_trace_id"] = trace_id
        if response.status_code >= 500:
            completed_fields["observability_signal"] = "api_server_error"
        log_fn("http_request", http_event="completed", **completed_fields)
        structlog.contextvars.clear_contextvars()

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response
