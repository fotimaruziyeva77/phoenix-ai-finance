"""
Unit tests: JWT access/refresh helpers (no database, no HTTP).

Uses an isolated ``Settings`` instance via env in ``tmp_path`` (no repo ``.env``).

Checklist
---------
3. Access token encodes/decodes with expected claims.
4. Refresh token encodes/decodes with expected claims (incl. ``jti``).
5. Wrong token *kind* is rejected (``expected_token_type`` / ``validate_token_type``).
6. Expired token is rejected.
7. Malformed token strings are rejected.

Edge cases (brief)
------------------
* **Strict expiry**: ``leeway=0`` on decode — small clock skew between issuers/consumers
  can theoretically cause false negatives; increase only with care.
* **Unknown ``token_type`` claim**: Must be exactly ``access`` or ``refresh`` after decode;
  any other string fails closed as invalid (not a type mismatch).
* **Wrong signing key**: Treated as malformed/invalid signature (same exception family as
  tampered tokens).
* **Refresh ``jti``**: Omitted from this module’s *creation* path (always set); supply your
  own ``jti`` when implementing rotation/blacklists.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from app.core.config import Settings, get_settings
from app.core.security.jwt_tokens import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    validate_token_type,
)
from app.core.security.token_errors import TokenExpiredError, TokenInvalidError, TokenTypeError
from app.services.auth_exceptions import JwtSecretNotConfiguredError


@pytest.fixture
def jwt_settings(monkeypatch, tmp_path) -> Settings:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JWT_SECRET_KEY", "unit_test_jwt_secret_key_min_32_chars!!")
    monkeypatch.setenv("APP_JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    monkeypatch.setenv("APP_JWT_REFRESH_TOKEN_EXPIRE_DAYS", "14")
    get_settings.cache_clear()
    s = Settings()
    yield s
    get_settings.cache_clear()


def test_access_token_decodes_with_expected_claims(jwt_settings: Settings):
    """Checklist (3): access JWT round-trip and required claims."""
    uid = uuid.uuid4()
    token = create_access_token(
        uid,
        "customer_admin",
        "user@example.com",
        settings=jwt_settings,
    )
    payload = decode_token(token, settings=jwt_settings, expected_token_type="access")
    assert payload["sub"] == str(uid)
    assert payload["role"] == "customer_admin"
    assert payload["email"] == "user@example.com"
    assert payload["token_type"] == TOKEN_TYPE_ACCESS


def test_refresh_token_decodes_with_expected_claims(jwt_settings: Settings):
    """Checklist (4): refresh JWT round-trip, ``jti``, and type."""
    uid = uuid.uuid4()
    token = create_refresh_token(uid, settings=jwt_settings)
    payload = decode_token(token, settings=jwt_settings, expected_token_type="refresh")
    assert payload["sub"] == str(uid)
    assert payload["token_type"] == TOKEN_TYPE_REFRESH
    assert "jti" in payload and len(str(payload["jti"])) > 0


def test_refresh_token_custom_jti_preserved(jwt_settings: Settings):
    uid = uuid.uuid4()
    custom = "rotation-stable-jti-001"
    token = create_refresh_token(uid, settings=jwt_settings, jti=custom)
    payload = decode_token(token, settings=jwt_settings)
    assert payload["jti"] == custom


def test_wrong_expected_token_type_rejected(jwt_settings: Settings):
    """Checklist (5): access token cannot satisfy refresh expectation (and vice versa)."""
    uid = uuid.uuid4()
    access = create_access_token(
        uid, "superadmin", "a@b.c", settings=jwt_settings
    )
    with pytest.raises(TokenTypeError):
        decode_token(access, settings=jwt_settings, expected_token_type="refresh")

    refresh = create_refresh_token(uid, settings=jwt_settings)
    with pytest.raises(TokenTypeError):
        decode_token(refresh, settings=jwt_settings, expected_token_type="access")


def test_validate_token_type_matches_payload(jwt_settings: Settings):
    uid = uuid.uuid4()
    token = create_refresh_token(uid, settings=jwt_settings)
    payload = decode_token(token, settings=jwt_settings)
    validate_token_type(payload, "refresh")
    with pytest.raises(TokenTypeError):
        validate_token_type(payload, "access")


def test_unknown_token_type_claim_rejected(jwt_settings: Settings):
    """``token_type`` must be access or refresh — other strings are invalid."""
    secret = jwt_settings.jwt_secret_key
    assert secret is not None
    now = datetime.now(UTC)
    bad = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "token_type": "admin",
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        secret,
        algorithm=jwt_settings.jwt_algorithm,
    )
    with pytest.raises(TokenInvalidError):
        decode_token(bad, settings=jwt_settings)


def test_expired_token_rejected(jwt_settings: Settings):
    """Checklist (6): past ``exp`` raises ``TokenExpiredError``."""
    uid = uuid.uuid4()
    secret = jwt_settings.jwt_secret_key
    assert secret is not None
    past = datetime.now(UTC) - timedelta(hours=1)
    bad = jwt.encode(
        {
            "sub": str(uid),
            "role": "customer_admin",
            "email": "e@e.e",
            "token_type": TOKEN_TYPE_ACCESS,
            "iat": past,
            "exp": past + timedelta(minutes=1),
        },
        secret,
        algorithm=jwt_settings.jwt_algorithm,
    )
    with pytest.raises(TokenExpiredError):
        decode_token(bad, settings=jwt_settings)


def test_malformed_token_rejected(jwt_settings: Settings):
    """Checklist (7): non-JWT strings and empty input."""
    with pytest.raises(TokenInvalidError):
        decode_token("not.a.jwt", settings=jwt_settings)
    with pytest.raises(TokenInvalidError):
        decode_token("", settings=jwt_settings)
    with pytest.raises(TokenInvalidError):
        decode_token("   ", settings=jwt_settings)


def test_wrong_signature_rejected(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)
    get_settings.cache_clear()
    s_sign = Settings()
    uid = uuid.uuid4()
    token = create_access_token(uid, "customer_admin", "u@u.u", settings=s_sign)
    monkeypatch.setenv("JWT_SECRET_KEY", "b" * 32)
    get_settings.cache_clear()
    s_verify = Settings()
    try:
        with pytest.raises(TokenInvalidError):
            decode_token(token, settings=s_verify)
    finally:
        get_settings.cache_clear()


def test_missing_token_type_claim_rejected(jwt_settings: Settings):
    secret = jwt_settings.jwt_secret_key
    assert secret is not None
    now = datetime.now(UTC)
    bad = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        secret,
        algorithm=jwt_settings.jwt_algorithm,
    )
    with pytest.raises(TokenInvalidError):
        decode_token(bad, settings=jwt_settings)


def test_create_access_token_without_secret_raises():
    cfg = Settings.model_construct(
        jwt_secret_key=None,
        jwt_algorithm="HS256",
        jwt_access_token_expire_minutes=15,
        jwt_refresh_token_expire_days=7,
    )
    with pytest.raises(JwtSecretNotConfiguredError, match="JWT_SECRET_KEY"):
        create_access_token(
            uuid.uuid4(), "customer_admin", "a@b.c", settings=cfg
        )
