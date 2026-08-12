"""Unit tests for :mod:`app.lib.integration_secrets_crypto`."""

from __future__ import annotations

import pytest
from app.core.config import Settings
from app.lib.integration_secrets_crypto import (
    IntegrationSecretCryptoError,
    decrypt_integration_secret,
    decrypt_integration_secret_legacy_jwt,
    encrypt_integration_secret,
    encrypt_integration_secret_legacy_jwt,
)


def _fernet_settings(key: str) -> Settings:
    return Settings.model_construct(
        jwt_secret_key="jwt-is-not-used-for-telegram-secrets-" + "x" * 8,
        telegram_token_fernet_key=key,
    )


def test_encrypt_decrypt_roundtrip() -> None:
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    settings = _fernet_settings(key)
    plain = "any-integration-secret-value"
    ct = encrypt_integration_secret(plain, settings)
    assert plain not in ct
    assert decrypt_integration_secret(ct, settings) == plain


def test_missing_telegram_fernet_key_raises() -> None:
    settings = Settings.model_construct(
        jwt_secret_key="x" * 32,
        telegram_token_fernet_key=None,
    )
    with pytest.raises(IntegrationSecretCryptoError, match="APP_TELEGRAM_TOKEN_FERNET_KEY"):
        encrypt_integration_secret("secret", settings)


def test_invalid_telegram_fernet_key_raises() -> None:
    settings = Settings.model_construct(
        jwt_secret_key="x" * 32,
        telegram_token_fernet_key="not-a-fernet-key",
    )
    with pytest.raises(IntegrationSecretCryptoError, match="not a valid Fernet"):
        encrypt_integration_secret("secret", settings)


def test_decrypt_wrong_key_raises() -> None:
    from cryptography.fernet import Fernet

    k1 = Fernet.generate_key().decode()
    k2 = Fernet.generate_key().decode()
    ct = encrypt_integration_secret("data", _fernet_settings(k1))
    with pytest.raises(IntegrationSecretCryptoError, match="Could not decrypt"):
        decrypt_integration_secret(ct, _fernet_settings(k2))


def test_empty_plaintext() -> None:
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    with pytest.raises(IntegrationSecretCryptoError):
        encrypt_integration_secret("  ", _fernet_settings(key))


def test_legacy_jwt_encrypt_decrypt_roundtrip() -> None:
    jwt_secret = "legacy-jwt-material-exactly-32bytes"
    plain = "telegram-bot-token"
    ct = encrypt_integration_secret_legacy_jwt(plain, jwt_secret)
    assert decrypt_integration_secret_legacy_jwt(ct, jwt_secret) == plain


def test_migration_reencrypt_off_legacy_to_dedicated_key() -> None:
    from cryptography.fernet import Fernet

    jwt_secret = "another-legacy-jwt-secret-key-32b"
    plain = "token-for-migration-test"
    legacy_ct = encrypt_integration_secret_legacy_jwt(plain, jwt_secret)
    new_key = Fernet.generate_key().decode()
    recovered = decrypt_integration_secret_legacy_jwt(legacy_ct, jwt_secret)
    new_ct = encrypt_integration_secret(recovered, _fernet_settings(new_key))
    assert decrypt_integration_secret(new_ct, _fernet_settings(new_key)) == plain


def test_jwt_secret_rotation_does_not_change_dedicated_ciphertext() -> None:
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    s1 = Settings.model_construct(jwt_secret_key="first-jwt-secret-key-32bytes!", telegram_token_fernet_key=key)
    s2 = Settings.model_construct(jwt_secret_key="rotated-jwt-secret-key-32bytes", telegram_token_fernet_key=key)
    ct = encrypt_integration_secret("same", s1)
    assert decrypt_integration_secret(ct, s2) == "same"
