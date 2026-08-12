"""OpenAPI ``responses`` bundles for auth routes (success + StandardErrorResponse errors)."""

from __future__ import annotations

from typing import Any

from fastapi import status

from app.core.error_response import StandardErrorResponse
from app.schemas.auth import AuthSessionResponse, RefreshSessionListResponse
from app.schemas.user import MeResponse, TokenResponse


def _std(description: str) -> dict[str, Any]:
    return {"model": StandardErrorResponse, "description": description}


REGISTER_OPENAPI_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_201_CREATED: {
        "model": AuthSessionResponse,
        "description": "Account created; session issued (Bearer JSON and/or Set-Cookie when cookie auth is on).",
    },
    status.HTTP_409_CONFLICT: _std(
        "Conflict — typically ``email_already_registered`` (category: authentication)."
    ),
    status.HTTP_422_UNPROCESSABLE_CONTENT: _std(
        "Body validation failed — ``code``: ``validation_error``; ``details``: FastAPI/Pydantic error list."
    ),
    status.HTTP_429_TOO_MANY_REQUESTS: _std(
        "Rate limited — ``code``: ``rate_limit_exceeded``; ``Retry-After`` header may be set (category: authentication)."
    ),
}

LOGIN_OPENAPI_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "model": AuthSessionResponse,
        "description": "Session issued (Bearer JSON and/or cookies per settings).",
    },
    status.HTTP_401_UNAUTHORIZED: _std(
        "Invalid email/password — ``invalid_credentials`` (category: authentication)."
    ),
    status.HTTP_403_FORBIDDEN: _std(
        "Account disabled — ``inactive_user`` (category: authentication)."
    ),
    status.HTTP_422_UNPROCESSABLE_CONTENT: _std(
        "Body validation failed — ``validation_error``."
    ),
    status.HTTP_429_TOO_MANY_REQUESTS: _std(
        "Rate limited — ``rate_limit_exceeded`` (category: authentication)."
    ),
}

REFRESH_OPENAPI_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "model": TokenResponse,
        "description": "New access+refresh pair (or cookies in cookie mode).",
    },
    status.HTTP_401_UNAUTHORIZED: _std(
        "Refresh rejected — ``invalid_refresh_token``, ``refresh_token_expired``, "
        "``refresh_token_revoked``, or ``refresh_token_reuse_detected`` (category: authentication)."
    ),
    status.HTTP_403_FORBIDDEN: _std(
        "CSRF check failed in cookie mode — ``csrf_validation_failed`` (category: authentication)."
    ),
    status.HTTP_422_UNPROCESSABLE_CONTENT: _std(
        "Missing refresh token — ``refresh_token_required`` (category: authentication), "
        "or ``validation_error`` for malformed body."
    ),
    status.HTTP_429_TOO_MANY_REQUESTS: _std("Rate limited — ``rate_limit_exceeded``."),
}

OAUTH_EXCHANGE_OPENAPI_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "model": AuthSessionResponse,
        "description": "OAuth session established (same shape as register/login).",
    },
    status.HTTP_401_UNAUTHORIZED: _std(
        "One-time exchange code invalid or reused — ``oauth_exchange_invalid`` (category: authentication)."
    ),
    status.HTTP_422_UNPROCESSABLE_CONTENT: _std("Body validation failed — ``validation_error``."),
    status.HTTP_429_TOO_MANY_REQUESTS: _std("Rate limited — ``rate_limit_exceeded``."),
}

LIST_SESSIONS_OPENAPI_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "model": RefreshSessionListResponse,
        "description": "Active refresh sessions for the current user.",
    },
    status.HTTP_401_UNAUTHORIZED: _std("Not authenticated — ``not_authenticated`` or ``token_expired``."),
}

ME_OPENAPI_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "model": MeResponse,
        "description": "Current user profile.",
    },
    status.HTTP_401_UNAUTHORIZED: _std("Missing/invalid access token — ``not_authenticated`` or ``token_expired``."),
}

LOGOUT_CURRENT_OPENAPI_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_204_NO_CONTENT: {"description": "Refresh session revoked; auth cookies cleared when cookie mode is on."},
    status.HTTP_400_BAD_REQUEST: _std("Invalid refresh — ``invalid_session`` (category: authentication)."),
    status.HTTP_403_FORBIDDEN: _std("CSRF failure in cookie mode — ``csrf_validation_failed``."),
    status.HTTP_422_UNPROCESSABLE_CONTENT: _std("Missing refresh token in body/cookie."),
    status.HTTP_429_TOO_MANY_REQUESTS: _std("Rate limited — ``rate_limit_exceeded``."),
}

LOGOUT_ALL_OPENAPI_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_204_NO_CONTENT: {"description": "All refresh sessions revoked; cookies cleared in cookie mode."},
    status.HTTP_401_UNAUTHORIZED: _std("Not authenticated."),
    status.HTTP_403_FORBIDDEN: _std("CSRF failure in cookie mode — ``csrf_validation_failed``."),
}

OAUTH_CALLBACK_OPENAPI_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_302_FOUND: {
        "description": (
            "Redirect to the configured frontend OAuth return URL. "
            "On success, query includes ``oauth_exchange_code`` (exchange via "
            "``POST /auth/oauth/exchange``). On failure, query includes ``oauth_error`` "
            "(stable code); optional ``detail`` may appear when error details are exposed."
        ),
        "headers": {
            "location": {
                "description": "Absolute URL with ``oauth_exchange_code`` or ``oauth_error`` query params.",
                "schema": {"type": "string"},
            }
        },
    },
    status.HTTP_429_TOO_MANY_REQUESTS: _std("Rate limited — ``rate_limit_exceeded``."),
}


LOGOUT_OPENAPI_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_204_NO_CONTENT: {"description": "Cookies cleared; optional Bearer session audit."},
    status.HTTP_403_FORBIDDEN: _std("CSRF failure in cookie mode — ``csrf_validation_failed``."),
    status.HTTP_429_TOO_MANY_REQUESTS: _std("Rate limited — ``rate_limit_exceeded``."),
}
