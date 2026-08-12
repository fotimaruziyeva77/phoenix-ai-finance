"""Signed, short-lived OAuth ``state`` (CSRF) using the app JWT secret."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.core.config import Settings
from app.core.security.jwt_tokens import require_jwt_secret
from app.services.auth_exceptions import (
    GithubOAuthInvalidStateError,
    GoogleOAuthInvalidStateError,
    OAuthInvalidStateError,
)

GOOGLE_OAUTH_STATE_FLOW = "google_oauth_v1"
GITHUB_OAUTH_STATE_FLOW = "github_oauth_v1"


def create_oauth_state(settings: Settings, flow: str) -> str:
    secret = require_jwt_secret(settings)
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=10)
    payload: dict[str, Any] = {
        "oauth_flow": flow,
        "iat": now,
        "exp": exp,
        "nonce": secrets.token_urlsafe(24),
    }
    return jwt.encode(
        payload,
        secret,
        algorithm=settings.jwt_algorithm,
        headers={"typ": "JWT"},
    )


def verify_oauth_state(state: str | None, settings: Settings, expected_flow: str) -> None:
    if not state or not str(state).strip():
        raise OAuthInvalidStateError("Missing OAuth state")
    secret = require_jwt_secret(settings)
    try:
        payload = jwt.decode(
            str(state).strip(),
            secret,
            algorithms=[settings.jwt_algorithm],
            options={
                "require": ["exp", "iat", "oauth_flow"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
            },
            leeway=0,
        )
    except ExpiredSignatureError as e:
        raise OAuthInvalidStateError("OAuth state has expired") from e
    except InvalidTokenError as e:
        raise OAuthInvalidStateError("Invalid OAuth state") from e

    if cast(dict[str, Any], payload).get("oauth_flow") != expected_flow:
        raise OAuthInvalidStateError("Invalid OAuth state")


def create_google_oauth_state(settings: Settings) -> str:
    return create_oauth_state(settings, GOOGLE_OAUTH_STATE_FLOW)


def verify_google_oauth_state(state: str | None, settings: Settings) -> None:
    try:
        verify_oauth_state(state, settings, GOOGLE_OAUTH_STATE_FLOW)
    except OAuthInvalidStateError as e:
        raise GoogleOAuthInvalidStateError(e.message) from e


def create_github_oauth_state(settings: Settings) -> str:
    return create_oauth_state(settings, GITHUB_OAUTH_STATE_FLOW)


def verify_github_oauth_state(state: str | None, settings: Settings) -> None:
    try:
        verify_oauth_state(state, settings, GITHUB_OAUTH_STATE_FLOW)
    except OAuthInvalidStateError as e:
        raise GithubOAuthInvalidStateError(e.message) from e
