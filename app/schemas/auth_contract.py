"""
Canonical auth API contracts (documentation + shared constants).

Success bodies are the same Pydantic models used at runtime
(:class:`~app.schemas.auth.AuthSessionResponse`, etc.). This module adds:

* Stable **machine codes** for clients (must match :mod:`app.services.auth_exceptions`).
* **OAuth browser redirect** query shape (not JSON — SPA parses ``location`` URL).
"""

from __future__ import annotations

from typing import Final

# --- Success shapes (re-export for a single import path in docs / tools) ---

from app.schemas.auth import (
    AuthBootstrapResponse,
    AuthSessionResponse,
    RefreshSessionListResponse,
    SessionStatusResponse,
)
from app.schemas.user import LoginRequest, MeResponse, RefreshRequest, TokenResponse, UserCreate

# --- OAuth redirect (frontend parses query string on FRONTEND_OAUTH_REDIRECT_URL) ---

OAUTH_CALLBACK_QUERY_OAUTH_ERROR: Final[str] = "oauth_error"
OAUTH_CALLBACK_QUERY_EXCHANGE_CODE: Final[str] = "oauth_exchange_code"
OAUTH_CALLBACK_QUERY_DETAIL: Final[str] = "detail"

# Typical Google/GitHub failure redirect:
# ``{FRONTEND_OAUTH_REDIRECT_URL}?oauth_error=<code>&detail=...`` (detail optional)

# --- Auth domain error codes by HTTP status (StandardErrorResponse.error.code) ---

AUTH_ERROR_CODES_400: Final[frozenset[str]] = frozenset(
    {
        "invalid_session",  # logout-current: bad refresh
        "google_oauth_invalid_state",
        "github_oauth_invalid_state",
        "oauth_invalid_state",
    }
)

AUTH_ERROR_CODES_401: Final[frozenset[str]] = frozenset(
    {
        "not_authenticated",
        "invalid_credentials",
        "invalid_refresh_token",
        "refresh_token_expired",
        "refresh_token_revoked",
        "refresh_token_reuse_detected",
        "oauth_exchange_invalid",
        "token_expired",
        "unauthorized",  # generic StarletteHTTPException 401
    }
)

AUTH_ERROR_CODES_403: Final[frozenset[str]] = frozenset(
    {
        "inactive_user",
        "csrf_validation_failed",
        "google_email_not_verified",
        "github_oauth_email_unavailable",
        "forbidden",  # generic HTTP 403
    }
)

AUTH_ERROR_CODES_409: Final[frozenset[str]] = frozenset(
    {
        "email_already_registered",
        "google_oauth_link_conflict",
        "github_oauth_link_conflict",
    }
)

AUTH_ERROR_CODES_422: Final[frozenset[str]] = frozenset({"validation_error", "refresh_token_required"})

AUTH_ERROR_CODES_429: Final[frozenset[str]] = frozenset({"rate_limit_exceeded"})

ALL_DOCUMENTED_AUTH_ERROR_CODES: Final[frozenset[str]] = (
    AUTH_ERROR_CODES_400
    | AUTH_ERROR_CODES_401
    | AUTH_ERROR_CODES_403
    | AUTH_ERROR_CODES_409
    | AUTH_ERROR_CODES_422
    | AUTH_ERROR_CODES_429
)

__all__ = [
    "ALL_DOCUMENTED_AUTH_ERROR_CODES",
    "AUTH_ERROR_CODES_400",
    "AUTH_ERROR_CODES_401",
    "AUTH_ERROR_CODES_403",
    "AUTH_ERROR_CODES_409",
    "AUTH_ERROR_CODES_422",
    "AUTH_ERROR_CODES_429",
    "AuthBootstrapResponse",
    "AuthSessionResponse",
    "LoginRequest",
    "MeResponse",
    "OAUTH_CALLBACK_QUERY_DETAIL",
    "OAUTH_CALLBACK_QUERY_EXCHANGE_CODE",
    "OAUTH_CALLBACK_QUERY_OAUTH_ERROR",
    "RefreshRequest",
    "RefreshSessionListResponse",
    "SessionStatusResponse",
    "TokenResponse",
    "UserCreate",
]
