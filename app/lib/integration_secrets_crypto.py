"""
Fernet encryption for Telegram integration secrets at rest.

**Telegram bot tokens** and **webhook ``secret_token``** ciphertexts use **only**
``APP_TELEGRAM_TOKEN_FERNET_KEY`` (or ``TELEGRAM_TOKEN_FERNET_KEY``). They are **not**
derived from ``JWT_SECRET_KEY`` — JWT rotation must never break Telegram decryption.

**Migration:** If rows were encrypted with the historical JWT-derived key, use
:func:`decrypt_integration_secret_legacy_jwt` plus :func:`encrypt_integration_secret` with a
settings object that carries the new Fernet key, or run ``scripts/reencrypt_telegram_secrets.py``.

Never log plaintext or ciphertext.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings


class IntegrationSecretCryptoError(Exception):
    """Invalid plaintext, ciphertext, or encryption configuration."""


class IntegrationSecretKeyConfigurationError(IntegrationSecretCryptoError):
    """Dedicated Fernet key missing or invalid; set ``APP_TELEGRAM_TOKEN_FERNET_KEY``."""


def _fernet_key_from_material(secret: str) -> bytes:
    """Historical: SHA-256 digest urlsafe-b64 used when Fernet key was derived from JWT."""
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def build_fernet_for_integration_secrets(settings: Settings) -> Fernet:
    """Build Fernet from ``settings.telegram_token_fernet_key`` only (no JWT fallback)."""
    explicit = (settings.telegram_token_fernet_key or "").strip()
    if not explicit:
        raise IntegrationSecretKeyConfigurationError(
            "APP_TELEGRAM_TOKEN_FERNET_KEY is not set. "
            "Telegram bot tokens and webhook secrets at rest require a dedicated Fernet key "
            "(generate: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"). "
            "This key is independent of JWT_SECRET_KEY.",
        )
    try:
        return Fernet(explicit.encode("utf-8"))
    except ValueError as exc:
        raise IntegrationSecretKeyConfigurationError(
            "APP_TELEGRAM_TOKEN_FERNET_KEY is not a valid Fernet key (use Fernet.generate_key()).",
        ) from exc


def encrypt_integration_secret(plaintext: str, settings: Settings) -> str:
    """Return URL-safe ASCII ciphertext for database storage."""
    f = build_fernet_for_integration_secrets(settings)
    secret = (plaintext or "").strip()
    if not secret:
        raise IntegrationSecretCryptoError("Secret is empty.")
    return f.encrypt(secret.encode("utf-8")).decode("ascii")


def decrypt_integration_secret(ciphertext: str, settings: Settings) -> str:
    """Decrypt a stored integration secret using ``APP_TELEGRAM_TOKEN_FERNET_KEY``."""
    f = build_fernet_for_integration_secrets(settings)
    raw = (ciphertext or "").strip()
    if not raw:
        raise IntegrationSecretCryptoError("Stored secret ciphertext is empty.")
    try:
        return f.decrypt(raw.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise IntegrationSecretCryptoError(
            "Could not decrypt secret (wrong APP_TELEGRAM_TOKEN_FERNET_KEY or corrupt ciphertext).",
        ) from exc


def _legacy_fernet_from_jwt_secret(jwt_secret: str) -> Fernet:
    jwt = (jwt_secret or "").strip()
    if not jwt:
        raise IntegrationSecretCryptoError("Legacy JWT material is empty.")
    return Fernet(_fernet_key_from_material(jwt))


def decrypt_integration_secret_legacy_jwt(ciphertext: str, jwt_secret: str) -> str:
    """
    Decrypt ciphertext produced by older deployments that derived Fernet from ``JWT_SECRET_KEY``.

    **Migration / tooling only** — not used by runtime request paths.
    """
    f = _legacy_fernet_from_jwt_secret(jwt_secret)
    raw = (ciphertext or "").strip()
    if not raw:
        raise IntegrationSecretCryptoError("Stored secret ciphertext is empty.")
    try:
        return f.decrypt(raw.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise IntegrationSecretCryptoError(
            "Could not decrypt with legacy JWT-derived key (wrong JWT_SECRET_KEY or corrupt data).",
        ) from exc


def encrypt_integration_secret_legacy_jwt(plaintext: str, jwt_secret: str) -> str:
    """
    Encrypt using the legacy JWT-derived Fernet key.

    **Tests and migration verification only.**
    """
    f = _legacy_fernet_from_jwt_secret(jwt_secret)
    secret = (plaintext or "").strip()
    if not secret:
        raise IntegrationSecretCryptoError("Secret is empty.")
    return f.encrypt(secret.encode("utf-8")).decode("ascii")
