"""
JWT access and refresh tokens.

Uses explicit ``token_type`` claim (``access`` | ``refresh``). Refresh tokens
include ``jti`` for future rotation/blacklisting without API churn.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.core.config import Settings, get_settings
from app.core.security.token_errors import (
    TokenExpiredError,
    TokenInvalidError,
    TokenTypeError,
)
from app.services.auth_exceptions import JwtSecretNotConfiguredError

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"
TokenTypeLiteral = Literal["access", "refresh"]

_REQUIRED_CLAIMS = ("exp", "iat", "sub", "token_type")


def _require_jwt_secret(settings: Settings) -> str:
    key = settings.jwt_secret_key
    if not key:
        raise JwtSecretNotConfiguredError(
            "Set JWT_SECRET_KEY or APP_JWT_SECRET_KEY (required for API tokens and OAuth state).",
        )
    return key


# Used by OAuth state signing and other modules that share the app JWT secret.
require_jwt_secret = _require_jwt_secret


def create_access_token(
    user_id: uuid.UUID,
    role: str,
    email: str,
    *,
    settings: Settings | None = None,
) -> str:
    """Sign a short-lived access JWT (``sub``, ``role``, ``email``, ``token_type=access``)."""
    cfg = settings or get_settings()
    secret = _require_jwt_secret(cfg)
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=cfg.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "email": email,
        "token_type": TOKEN_TYPE_ACCESS,
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(
        payload,
        secret,
        algorithm=cfg.jwt_algorithm,
        headers={"typ": "JWT"},
    )


def create_impersonation_token(
    target_user_id: uuid.UUID,
    target_role: str,
    target_email: str,
    impersonated_by: uuid.UUID,
    *,
    settings: Settings | None = None,
) -> str:
    """Sign a short-lived (15-min) impersonation access token with ``impersonated_by`` claim."""
    cfg = settings or get_settings()
    secret = _require_jwt_secret(cfg)
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=15)
    payload: dict[str, Any] = {
        "sub": str(target_user_id),
        "role": target_role,
        "email": target_email,
        "token_type": TOKEN_TYPE_ACCESS,
        "impersonated_by": str(impersonated_by),
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(
        payload,
        secret,
        algorithm=cfg.jwt_algorithm,
        headers={"typ": "JWT"},
    )


def create_refresh_token(
    user_id: uuid.UUID,
    *,
    settings: Settings | None = None,
    jti: str | None = None,
    family_id: uuid.UUID | None = None,
) -> str:
    """
    Sign a refresh JWT (``sub``, ``token_type=refresh``, ``jti``, optional ``fid`` family id).

    Pass ``family_id`` for rotation chains; omit for a new login/device family.
    """
    cfg = settings or get_settings()
    secret = _require_jwt_secret(cfg)
    now = datetime.now(UTC)
    exp = now + timedelta(days=cfg.jwt_refresh_token_expire_days)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "token_type": TOKEN_TYPE_REFRESH,
        "jti": jti or str(uuid.uuid4()),
        "iat": now,
        "exp": exp,
    }
    if family_id is not None:
        payload["fid"] = str(family_id)
    return jwt.encode(
        payload,
        secret,
        algorithm=cfg.jwt_algorithm,
        headers={"typ": "JWT"},
    )


def decode_token(
    token: str,
    *,
    settings: Settings | None = None,
    expected_token_type: TokenTypeLiteral | None = None,
) -> dict[str, Any]:
    """
    Decode and validate a JWT.

    - Enforces algorithm allow-list from settings (no ``none``).
    - Requires ``exp``, ``iat``, ``sub``, ``token_type``.
    - If ``expected_token_type`` is set, it must match the claim exactly.

    Returns:
        Payload dict (claims). Does not mutate or log the token.

    Raises:
        TokenExpiredError: past ``exp``.
        TokenTypeError: wrong ``token_type`` when ``expected_token_type`` is set.
        TokenInvalidError: malformed, bad signature, missing claims, etc.
    """
    if not isinstance(token, str) or not token.strip():
        raise TokenInvalidError("token must be a non-empty string")

    cfg = settings or get_settings()
    secret = _require_jwt_secret(cfg)
    algorithm = cfg.jwt_algorithm

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            options={
                "require": list(_REQUIRED_CLAIMS),
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
            },
            leeway=0,
        )
    except ExpiredSignatureError as e:
        raise TokenExpiredError("token has expired") from e
    except InvalidTokenError as e:
        raise TokenInvalidError(str(e) or "invalid token") from e

    tt = payload.get("token_type")
    if tt not in (TOKEN_TYPE_ACCESS, TOKEN_TYPE_REFRESH):
        raise TokenInvalidError("invalid or missing token_type claim")

    if expected_token_type is not None and tt != expected_token_type:
        raise TokenTypeError(
            f"expected token_type {expected_token_type!r}, got {tt!r}",
        )

    return cast(dict[str, Any], payload)


def validate_token_type(
    payload: dict[str, Any],
    expected: TokenTypeLiteral,
) -> None:
    """
    Assert payload ``token_type`` matches ``expected``.

    Raises:
        TokenTypeError: mismatch or missing claim.
        TokenInvalidError: claim present but not a known type.
    """
    tt = payload.get("token_type")
    if tt not in (TOKEN_TYPE_ACCESS, TOKEN_TYPE_REFRESH):
        raise TokenInvalidError("invalid or missing token_type claim")
    if tt != expected:
        raise TokenTypeError(f"expected token_type {expected!r}, got {tt!r}")
