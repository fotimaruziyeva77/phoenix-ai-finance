"""OAuth state JWT (CSRF) signing and verification."""

from __future__ import annotations

import jwt
from app.core.config import Settings
from app.integrations.oauth_state import create_google_oauth_state, verify_google_oauth_state
from app.services.auth_exceptions import GoogleOAuthInvalidStateError


def test_google_oauth_state_round_trip() -> None:
    settings = Settings(
        jwt_secret_key="x" * 32,
        jwt_algorithm="HS256",
        environment="local",
    )
    token = create_google_oauth_state(settings)
    verify_google_oauth_state(token, settings)


def test_google_oauth_state_rejects_wrong_secret() -> None:
    a = Settings(jwt_secret_key="a" * 32, jwt_algorithm="HS256", environment="local")
    b = Settings(jwt_secret_key="b" * 32, jwt_algorithm="HS256", environment="local")
    token = create_google_oauth_state(a)
    try:
        verify_google_oauth_state(token, b)
    except GoogleOAuthInvalidStateError:
        return
    raise AssertionError("expected GoogleOAuthInvalidStateError")


def test_google_oauth_state_rejects_tampered_flow() -> None:
    settings = Settings(jwt_secret_key="x" * 32, jwt_algorithm="HS256", environment="local")
    token = create_google_oauth_state(settings)
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"verify_signature": False},
    )
    payload["oauth_flow"] = "evil"
    bad = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    try:
        verify_google_oauth_state(bad, settings)
    except GoogleOAuthInvalidStateError:
        return
    raise AssertionError("expected GoogleOAuthInvalidStateError")
