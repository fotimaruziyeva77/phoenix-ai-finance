"""HttpOnly auth cookies + double-submit CSRF cookie for SPA cookie mode."""

from __future__ import annotations

import secrets

from starlette.responses import Response

from app.core.config import Settings


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def access_cookie_value(request, settings: Settings) -> str | None:
    return request.cookies.get(settings.auth_access_cookie_name)


def refresh_cookie_value(request, settings: Settings) -> str | None:
    return request.cookies.get(settings.auth_refresh_cookie_name)


def csrf_cookie_value(request, settings: Settings) -> str | None:
    raw = request.cookies.get(settings.auth_csrf_cookie_name)
    return raw if raw else None


def attach_session_cookies(
    response: Response,
    settings: Settings,
    *,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
    access_max_age_seconds: int,
    refresh_max_age_seconds: int,
) -> None:
    """Set access + refresh (httpOnly) and CSRF (readable by JS for header echo)."""
    common = {
        "path": settings.auth_cookie_path,
        "secure": settings.auth_cookie_secure_effective,
        "samesite": settings.auth_cookie_same_site.lower(),  # type: ignore[arg-type]
    }
    domain = settings.auth_cookie_domain
    if domain:
        common["domain"] = domain

    response.set_cookie(
        settings.auth_access_cookie_name,
        access_token,
        httponly=True,
        max_age=access_max_age_seconds,
        **common,
    )
    response.set_cookie(
        settings.auth_refresh_cookie_name,
        refresh_token,
        httponly=True,
        max_age=refresh_max_age_seconds,
        **common,
    )
    # Double-submit: not httpOnly so SPA can read and send X-CSRF-Token
    response.set_cookie(
        settings.auth_csrf_cookie_name,
        csrf_token,
        httponly=False,
        max_age=refresh_max_age_seconds,
        **common,
    )


def clear_session_cookies(response: Response, settings: Settings) -> None:
    common = {
        "path": settings.auth_cookie_path,
        "secure": settings.auth_cookie_secure_effective,
        "samesite": settings.auth_cookie_same_site.lower(),  # type: ignore[arg-type]
    }
    domain = settings.auth_cookie_domain
    if domain:
        common["domain"] = domain
    for name in (
        settings.auth_access_cookie_name,
        settings.auth_refresh_cookie_name,
        settings.auth_csrf_cookie_name,
    ):
        response.delete_cookie(name, **common)


def csrf_header_matches_cookie(request, settings: Settings) -> bool:
    cookie_t = csrf_cookie_value(request, settings)
    header_t = request.headers.get(settings.auth_csrf_header_name)
    if not cookie_t or not header_t or len(cookie_t) != len(header_t):
        return False
    return secrets.compare_digest(cookie_t, header_t)
