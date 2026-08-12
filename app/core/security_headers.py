"""
Baseline security response headers (CSP, HSTS, framing, referrer).

CSP is built once at import time from settings; extra ``connect-src`` and
``script-src`` origins can be added via ``APP_SECURITY_CSP_EXTRA_CONNECT_SRC``
and ``APP_SECURITY_CSP_EXTRA_SCRIPT_SRC`` without code changes.

HSTS is fully configurable: max-age, includeSubDomains, preload.
"""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings, get_settings


def _build_csp(settings: Settings) -> str:
    """Assemble CSP header value, merging hardcoded defaults with env extras."""
    extra_connect = settings.security_csp_extra_connect_src.strip()
    extra_script = settings.security_csp_extra_script_src.strip()

    connect_src = "'self' https://api.stripe.com https://generativelanguage.googleapis.com"
    if extra_connect:
        connect_src += f" {extra_connect}"

    script_src = "'self' https://js.stripe.com"
    if extra_script:
        script_src += f" {extra_script}"

    return (
        f"default-src 'self'; "
        f"script-src {script_src}; "
        f"style-src 'self' 'unsafe-inline'; "
        f"img-src 'self' data: https:; "
        f"font-src 'self' data:; "
        f"connect-src {connect_src}; "
        f"frame-src https://js.stripe.com https://hooks.stripe.com; "
        f"object-src 'none'; "
        f"base-uri 'self'; "
        f"form-action 'self'"
    )


def _build_hsts(settings: Settings) -> str | None:
    """Build HSTS header or ``None`` when disabled."""
    if not settings.security_enable_hsts:
        return None
    value = f"max-age={settings.security_hsts_max_age}"
    if settings.security_hsts_include_subdomains:
        value += "; includeSubDomains"
    if settings.security_hsts_preload:
        value += "; preload"
    return value


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds conservative security headers on every response.

    * ``X-Content-Type-Options: nosniff``
    * ``X-Frame-Options: DENY``
    * ``Referrer-Policy: strict-origin-when-cross-origin``
    * ``Permissions-Policy`` — disables sensitive device APIs the app does not use
    * ``Content-Security-Policy`` — configurable via env vars
    * ``Strict-Transport-Security`` — optional, configurable
    * ``Cross-Origin-Opener-Policy: same-origin``
    * ``Cross-Origin-Resource-Policy: same-origin``
    * ``X-Permitted-Cross-Domain-Policies: none``
    """

    def __init__(self, app: object) -> None:  # noqa: ANN001
        super().__init__(app)  # type: ignore[arg-type]
        settings = get_settings()
        self._csp = _build_csp(settings)
        self._hsts = _build_hsts(settings)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        response = await call_next(request)

        # Core headers — always set.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()",
        )

        # CSP — built once from settings.
        response.headers["Content-Security-Policy"] = self._csp

        # Cross-origin isolation.
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # HSTS — only when explicitly enabled (HTTPS deployments).
        if self._hsts:
            response.headers.setdefault("Strict-Transport-Security", self._hsts)

        return response
