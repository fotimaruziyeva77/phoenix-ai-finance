"""User and auth API shapes (no ORM leakage beyond documented fields)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import OAuthProvider, UserRole


class UserCreate(BaseModel):
    """Registration payload; role is assigned server-side (default customer_admin)."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=256)


class UserRead(BaseModel):
    """Safe user projection (no secrets)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class MeResponse(UserRead):
    """Authenticated profile; optional fields reserved for verification and billing."""

    has_password: bool = Field(
        default=True,
        description="False for OAuth-only accounts (no password set).",
    )
    email_verified_at: datetime | None = Field(
        default=None,
        description="Set when email verification is implemented.",
    )
    plan_key: str | None = Field(
        default=None,
        max_length=64,
        description="Reserved for subscription/plan when persisted.",
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    auth_transport: Literal["bearer", "cookie"] = "bearer"
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int = Field(ge=1, description="Access token lifetime in seconds.")
    csrf_token: str | None = Field(
        default=None,
        description="Present when rotating session in cookie mode (send as X-CSRF-Token on subsequent mutating requests).",
    )


class RefreshRequest(BaseModel):
    """Body optional when refresh token is sent as HttpOnly cookie (cookie auth mode)."""

    refresh_token: str | None = Field(default=None, min_length=1)


class UserUpdate(BaseModel):
    """Mutable profile fields (PATCH /auth/me)."""

    full_name: str | None = Field(default=None, max_length=256)


class OAuthCallbackRequest(BaseModel):
    """OAuth redirect/callback body (authorization code flow)."""

    provider: OAuthProvider
    code: str = Field(min_length=1, max_length=4096)
    state: str | None = Field(default=None, max_length=2048)
    redirect_uri: str | None = Field(
        default=None,
        max_length=2048,
        description="Optional; required by some providers for token exchange.",
    )
