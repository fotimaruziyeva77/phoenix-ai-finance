"""Auth API response shapes."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserRead


class OAuthCallbackErrorInfo(BaseModel):
    """Documented shape for SPA OAuth return URL query (``oauth_error`` + optional ``detail``)."""

    oauth_error: str = Field(description="Stable machine-readable error code from the API redirect.")
    detail: str | None = Field(default=None, description="Human hint when APP_EXPOSE_ERROR_DETAILS is true.")


class OAuthExchangeRequest(BaseModel):
    """Exchange a one-time code from the OAuth redirect for API tokens (MVP in-memory store)."""

    exchange_code: str = Field(min_length=8, max_length=512)


class AuthSessionResponse(BaseModel):
    """
    After register, login, or OAuth exchange.

    * ``auth_transport=bearer``: tokens in this JSON (legacy / non-cookie deployments).
    * ``auth_transport=cookie``: HttpOnly cookies hold tokens; body may omit them when configured.
    * ``csrf_token``: when using cookie mode, echo as ``X-CSRF-Token`` on mutating requests.
    """

    auth_transport: Literal["bearer", "cookie"] = "bearer"
    user: UserRead
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int = Field(ge=1, description="Access token lifetime in seconds.")
    csrf_token: str | None = Field(
        default=None,
        description="CSRF value for double-submit (also set as non-httpOnly cookie when cookie mode is on).",
    )


class SessionStatusResponse(BaseModel):
    """``GET /auth/session`` — optional auth probe (never 401)."""

    authenticated: bool


class AuthBootstrapResponse(BaseModel):
    """Single-call SPA hydration (Bearer or cookie access)."""

    authenticated: bool
    auth_transport: Literal["bearer", "cookie", "none"] = "none"
    user: UserRead | None = None
    csrf_token: str | None = Field(
        default=None,
        description="CSRF cookie value when cookie auth is enabled (for X-CSRF-Token header).",
    )


class RefreshSessionRead(BaseModel):
    """Active refresh session row (no token or hash exposed)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    family_id: UUID
    jti: str
    issued_at: datetime
    expires_at: datetime
    rotated_from_jti: str | None = None
    device_info: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime
    updated_at: datetime


class RefreshSessionListResponse(BaseModel):
    items: list[RefreshSessionRead]
