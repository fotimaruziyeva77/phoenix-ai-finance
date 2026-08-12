#!/usr/bin/env python3
"""
One-shot migration: re-encrypt ``telegram_configs`` rows from legacy JWT-derived Fernet to
``APP_TELEGRAM_TOKEN_FERNET_KEY``.

**When:** Deployments that previously encrypted Telegram tokens using ``JWT_SECRET_KEY`` (removed).
**Before run:** Back up the database.

Environment (required):
  DATABASE_URL          — async URL (e.g. postgresql+asyncpg://...)
  LEGACY_JWT_SECRET_KEY — JWT secret that was used to derive the old Fernet key (same value apps used
                          before dedicated telegram key; must match encryption-time JWT).
  APP_TELEGRAM_TOKEN_FERNET_KEY — New dedicated Fernet key (Fernet.generate_key() output).

Usage:
  python scripts/reencrypt_telegram_secrets.py [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys


async def _run(*, dry_run: bool) -> int:
    database_url = (os.environ.get("DATABASE_URL") or os.environ.get("APP_DATABASE_URL") or "").strip()
    legacy_jwt = (
        os.environ.get("LEGACY_JWT_SECRET_KEY") or os.environ.get("JWT_SECRET_KEY_LEGACY") or ""
    ).strip()
    new_key = (os.environ.get("APP_TELEGRAM_TOKEN_FERNET_KEY") or "").strip()

    if not database_url:
        print("DATABASE_URL (or APP_DATABASE_URL) is required.", file=sys.stderr)
        return 2
    if not legacy_jwt:
        print(
            "LEGACY_JWT_SECRET_KEY (or JWT_SECRET_KEY_LEGACY) is required — the JWT used for old ciphertext.",
            file=sys.stderr,
        )
        return 2
    if not new_key:
        print("APP_TELEGRAM_TOKEN_FERNET_KEY is required (new dedicated Fernet key).", file=sys.stderr)
        return 2

    from cryptography.fernet import Fernet

    try:
        Fernet(new_key.encode("utf-8"))
    except ValueError as e:
        print(f"APP_TELEGRAM_TOKEN_FERNET_KEY is not a valid Fernet key: {e}", file=sys.stderr)
        return 2

    from app.core.config import Settings
    from app.core.db import normalize_database_url
    from app.lib.integration_secrets_crypto import (
        decrypt_integration_secret_legacy_jwt,
        encrypt_integration_secret,
    )
    from app.models.telegram_config import TelegramConfig
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    settings_new = Settings.model_construct(telegram_token_fernet_key=new_key)
    engine = create_async_engine(normalize_database_url(database_url), pool_pre_ping=True)
    sm = async_sessionmaker(engine, class_=AsyncSession, autoflush=False, expire_on_commit=False)
    updated = 0
    async with sm() as session:
        result = await session.execute(select(TelegramConfig))
        rows = list(result.scalars().all())
        for row in rows:
            try:
                plain_token = decrypt_integration_secret_legacy_jwt(row.bot_token_encrypted, legacy_jwt)
            except Exception as exc:
                print(f"bot_id={row.bot_id} bot_token decrypt failed: {exc}", file=sys.stderr)
                return 1
            new_tok = encrypt_integration_secret(plain_token, settings_new)

            new_wh = row.webhook_secret_token_encrypted
            if row.webhook_secret_token_encrypted:
                try:
                    plain_wh = decrypt_integration_secret_legacy_jwt(
                        row.webhook_secret_token_encrypted, legacy_jwt
                    )
                except Exception as exc:
                    print(f"bot_id={row.bot_id} webhook_secret decrypt failed: {exc}", file=sys.stderr)
                    return 1
                new_wh = encrypt_integration_secret(plain_wh, settings_new)

            if dry_run:
                print(f"dry-run bot_id={row.bot_id} would re-encrypt token + webhook secret")
            else:
                row.bot_token_encrypted = new_tok
                row.webhook_secret_token_encrypted = new_wh
            updated += 1

        if not dry_run and updated:
            await session.commit()

    await engine.dispose()
    print(f"{'Would update' if dry_run else 'Updated'} {updated} telegram_config row(s).")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Re-encrypt Telegram secrets for dedicated Fernet key.")
    p.add_argument("--dry-run", action="store_true", help="Parse and decrypt only; no DB writes.")
    args = p.parse_args()
    try:
        rc = asyncio.run(_run(dry_run=bool(args.dry_run)))
    except KeyboardInterrupt:
        rc = 130
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
