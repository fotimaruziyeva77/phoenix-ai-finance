# Telegram integration secrets (Fernet)

## Threat addressed

Historically, Telegram ciphertext could fall back to a **JWT-derived** Fernet key. **Rotating `JWT_SECRET_KEY` then broke decryption** of stored bot tokens and webhook `secret_token` values.

## Current behavior

- **Encryption key:** `APP_TELEGRAM_TOKEN_FERNET_KEY` (alias `TELEGRAM_TOKEN_FERNET_KEY`) — output of `cryptography.fernet.Fernet.generate_key()` (url-safe base64, 32-byte key).
- **Scope:** `telegram_configs.bot_token_encrypted` and `telegram_configs.webhook_secret_token_encrypted`.
- **JWT:** `JWT_SECRET_KEY` is **never** used for these fields at runtime.
- **Strict deploys:** `APP_ENVIRONMENT` ∈ `staging`, `production`, `prod` → key **required** and **validated** at settings load (fail fast).

## Operations

### New deploy

1. Generate a key:  
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
2. Store in secrets manager as `APP_TELEGRAM_TOKEN_FERNET_KEY`.
3. Rotate this key on its own schedule; rotate JWT independently.

### Migrating old rows (JWT-derived ciphertext)

1. **Backup the database.**
2. Set `LEGACY_JWT_SECRET_KEY` to the JWT secret that was active when rows were written.
3. Set `APP_TELEGRAM_TOKEN_FERNET_KEY` to the **new** dedicated key.
4. Dry run:  
   `python scripts/reencrypt_telegram_secrets.py --dry-run`
5. Apply:  
   `python scripts/reencrypt_telegram_secrets.py`

### Wrong key symptoms

- Connect works for **new** rows; inbound webhooks **fail** to decrypt (`token_decrypt_failed` channel events).
- `IntegrationSecretCryptoError` / `TelegramTokenCryptoError`: wrong key or corrupt ciphertext.

## Security note

Treat `APP_TELEGRAM_TOKEN_FERNET_KEY` like a **data-encryption key** (KMS-backed in production). It is **not** an authentication or signing secret for HTTP; compromise exposes **at-rest** Telegram tokens unless you also rotate tokens with Telegram.
