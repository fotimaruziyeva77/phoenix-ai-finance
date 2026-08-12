"""Telegram bot token encryption (delegates to :mod:`app.lib.integration_secrets_crypto`)."""

from __future__ import annotations

from app.core.config import Settings
from app.lib.integration_secrets_crypto import (
    IntegrationSecretCryptoError,
    IntegrationSecretKeyConfigurationError,
    decrypt_integration_secret,
    encrypt_integration_secret,
)


class TelegramTokenCryptoError(Exception):
    """Invalid ciphertext or encryption configuration for Telegram tokens."""


class TelegramTokenConfigurationError(TelegramTokenCryptoError):
    """Fernet key missing or invalid (``APP_TELEGRAM_TOKEN_FERNET_KEY``)."""


def encrypt_telegram_bot_token(plaintext: str, settings: Settings) -> str:
    try:
        return encrypt_integration_secret(plaintext, settings)
    except IntegrationSecretKeyConfigurationError as exc:
        raise TelegramTokenConfigurationError(str(exc)) from exc
    except IntegrationSecretCryptoError as exc:
        raise TelegramTokenCryptoError(str(exc)) from exc


def decrypt_telegram_bot_token(ciphertext: str, settings: Settings) -> str:
    try:
        return decrypt_integration_secret(ciphertext, settings)
    except IntegrationSecretKeyConfigurationError as exc:
        raise TelegramTokenConfigurationError(str(exc)) from exc
    except IntegrationSecretCryptoError as exc:
        raise TelegramTokenCryptoError(str(exc)) from exc
