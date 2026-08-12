"""
Request timeout middleware — returns **504 Gateway Timeout** when a request
exceeds ``security_request_timeout_seconds`` (default 60 s).

Upload-heavy routes (matched by path prefix) get the longer
``security_upload_timeout_seconds`` budget instead.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.logging import get_logger

_log = get_logger(__name__)

# Path prefixes that receive the extended upload timeout.
_UPLOAD_PATH_PREFIXES: tuple[str, ...] = (
    "/api/v1/bots/",  # covers /bots/{id}/knowledge/files uploads
)


def _is_upload_route(path: str) -> bool:
    """Heuristic: path belongs to a file-upload family."""
    return any(path.startswith(p) for p in _UPLOAD_PATH_PREFIXES) and (
        path.endswith("/files") or "/files/" in path
    )


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Cancel the downstream handler if it exceeds the configured timeout."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        settings = get_settings()
        path = request.url.path

        if request.method == "POST" and _is_upload_route(path):
            timeout = settings.security_upload_timeout_seconds
        else:
            timeout = settings.security_request_timeout_seconds

        try:
            return await asyncio.wait_for(call_next(request), timeout=timeout)
        except asyncio.TimeoutError:
            _log.warning(
                "request_timeout",
                method=request.method,
                path=path,
                timeout_seconds=timeout,
            )
            return JSONResponse(
                status_code=504,
                content={
                    "error": {
                        "code": "request_timeout",
                        "message": f"Request exceeded the {timeout:.0f}s time limit.",
                    }
                },
            )
