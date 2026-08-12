"""JSON + Set-Cookie assembly for cookie auth mode."""

from __future__ import annotations

from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.core.auth_cookies import attach_session_cookies, clear_session_cookies, new_csrf_token
from app.core.config import Settings
from app.schemas.auth import AuthSessionResponse
from app.schemas.user import TokenResponse


def _access_max_age(settings: Settings) -> int:
    return int(settings.jwt_access_token_expire_minutes * 60)


def _refresh_max_age(settings: Settings) -> int:
    return int(settings.jwt_refresh_token_expire_days * 86400)


def json_auth_session_response(
    settings: Settings,
    session: AuthSessionResponse,
    *,
    status_code: int = 200,
) -> JSONResponse:
    """
    Build JSON from service session (always includes raw tokens internally).
    When cookie mode is on, attach cookies and optionally strip tokens from JSON.
    """
    access_token = session.access_token
    refresh_token = session.refresh_token
    if not access_token or not refresh_token:
        raise ValueError("AuthSessionResponse from service must include access and refresh tokens")

    csrf = new_csrf_token() if settings.auth_cookie_enabled else None
    omit = settings.auth_cookie_enabled and settings.auth_cookie_omit_body_tokens
    body = AuthSessionResponse(
        auth_transport="cookie" if settings.auth_cookie_enabled else "bearer",
        user=session.user,
        access_token=None if omit else access_token,
        refresh_token=None if omit else refresh_token,
        expires_in=session.expires_in,
        csrf_token=csrf if settings.auth_cookie_enabled else None,
    )
    resp = JSONResponse(content=body.model_dump(mode="json"), status_code=status_code)
    if settings.auth_cookie_enabled and csrf is not None:
        attach_session_cookies(
            resp,
            settings,
            access_token=access_token,
            refresh_token=refresh_token,
            csrf_token=csrf,
            access_max_age_seconds=_access_max_age(settings),
            refresh_max_age_seconds=_refresh_max_age(settings),
        )
    return resp


def json_token_response(
    settings: Settings,
    tokens: TokenResponse,
    *,
    status_code: int = 200,
) -> JSONResponse:
    access_token = tokens.access_token
    refresh_token = tokens.refresh_token
    if not access_token or not refresh_token:
        raise ValueError("TokenResponse from service must include access and refresh tokens")

    csrf = new_csrf_token() if settings.auth_cookie_enabled else None
    omit = settings.auth_cookie_enabled and settings.auth_cookie_omit_body_tokens
    body = TokenResponse(
        auth_transport="cookie" if settings.auth_cookie_enabled else "bearer",
        access_token=None if omit else access_token,
        refresh_token=None if omit else refresh_token,
        expires_in=tokens.expires_in,
        csrf_token=csrf if settings.auth_cookie_enabled else None,
    )
    resp = JSONResponse(content=body.model_dump(mode="json"), status_code=status_code)
    if settings.auth_cookie_enabled and csrf is not None:
        attach_session_cookies(
            resp,
            settings,
            access_token=access_token,
            refresh_token=refresh_token,
            csrf_token=csrf,
            access_max_age_seconds=_access_max_age(settings),
            refresh_max_age_seconds=_refresh_max_age(settings),
        )
    return resp


def merge_clear_cookies(settings: Settings, response: Response) -> None:
    if settings.auth_cookie_enabled:
        clear_session_cookies(response, settings)
