"""Unit tests for Telegram token Fernet wrapper."""

from __future__ import annotations

import pytest
from app.core.config import Settings
from app.lib.telegram_token_crypto import (
    TelegramTokenCryptoError,
    decrypt_telegram_bot_token,
    encrypt_telegram_bot_token,
)


def test_encrypt_decrypt_roundtrip_derived_key() -> None:
    settings = Settings.model_construct(
        jwt_secret_key="x" * 32,
        telegram_token_fernet_key=None,
    )
    plain = "123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    ct = encrypt_telegram_bot_token(plain, settings)
    assert plain not in ct
    assert decrypt_telegram_bot_token(ct, settings) == plain


def test_explicit_fernet_key() -> None:
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode("ascii")
    settings = Settings.model_construct(jwt_secret_key=None, telegram_token_fernet_key=key)
    plain = "987654321:ZZZyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
    ct = encrypt_telegram_bot_token(plain, settings)
    assert decrypt_telegram_bot_token(ct, settings) == plain


def test_empty_token_rejected() -> None:
    settings = Settings.model_construct(jwt_secret_key="k" * 32, telegram_token_fernet_key=None)
    with pytest.raises(TelegramTokenCryptoError):
        encrypt_telegram_bot_token("   ", settings)


def test_decrypt_garbage() -> None:
    settings = Settings.model_construct(jwt_secret_key="k" * 32, telegram_token_fernet_key=None)
    with pytest.raises(TelegramTokenCryptoError):
        decrypt_telegram_bot_token("not-fernet", settings)
