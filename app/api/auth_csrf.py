"""CSRF double-submit for cookie-authenticated browser clients."""

from __future__ import annotations

from fastapi import Request

from app.core.auth_cookies import csrf_header_matches_cookie, refresh_cookie_value
from app.core.config import Settings
from app.services.auth_exceptions import CsrfValidationError

# Suffixes of URL path (after /api/v1) for routes that must not require CSRF.
_CSRF_EXEMPT_PATH_SUFFIXES = (
    "/auth/register",
    "/auth/login",
    "/auth/oauth/exchange",
)


def is_csrf_exempt_path(path: str) -> bool:
    p = path.rstrip("/")
    return any(p.endswith(suffix) for suffix in _CSRF_EXEMPT_PATH_SUFFIXES)


def enforce_csrf_if_cookie_session(request: Request, settings: Settings) -> None:
    if not settings.auth_cookie_enabled:
        return
    if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
        return
    if is_csrf_exempt_path(request.url.path):
        return
    has_cookie = bool(
        request.cookies.get(settings.auth_access_cookie_name)
        or request.cookies.get(settings.auth_refresh_cookie_name)
    )
    if not has_cookie:
        return
    if not csrf_header_matches_cookie(request, settings):
        raise CsrfValidationError()


def read_refresh_token_from_request(request: Request, settings: Settings, body_token: str | None) -> str | None:
    raw = (body_token or "").strip() if body_token else ""
    if raw:
        return raw
    if settings.auth_cookie_enabled:
        v = refresh_cookie_value(request, settings)
        return v.strip() if v else None
    return None
