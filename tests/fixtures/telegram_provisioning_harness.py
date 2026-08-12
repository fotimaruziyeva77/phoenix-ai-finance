"""
Outer-boundary sandbox for Telegram provisioning integration tests.

Strategy
--------
* **Real stack**: FastAPI ``TestClient``, default ``get_telegram_config_service`` dependency
  (no ``TelegramConfigService`` subclass / constructor injection).
* **Sandboxed Telegram only**: monkeypatch the three symbols imported into
  ``app.services.telegram_config_service`` that represent outbound Telegram HTTP:

  * ``http_verify_telegram_bot_token`` (``getMe`` / token verification)
  * ``set_telegram_bot_webhook`` (``setWebhook``)
  * ``delete_telegram_bot_webhook`` (``deleteWebhook``)

  Production code paths inside :class:`~app.services.telegram_config_service.TelegramConfigService`
  (encrypt, duplicate-bot SQL, status transitions, commits) run unchanged.

* **Real PostgreSQL**: assertions use ``asyncpg`` against the same ``DATABASE_URL`` as the app.

This is the recommended pattern when you must prove behavior **inside BotForge** without calling
api.telegram.org. For true external E2E, run a manual/staging check with a real BotFather token
and a reachable HTTPS webhook URL.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import asyncpg
import pytest
from app.integrations.telegram_bot_api.errors import TelegramApiErrorKind, TelegramBotApiError
from app.integrations.telegram_bot_verify import (
    TelegramBotVerificationResult,
    TelegramTokenVerificationError,
)


def asyncpg_dsn(async_pg_url: str) -> str:
    if "+asyncpg" in async_pg_url:
        return async_pg_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return async_pg_url


@dataclass
class TelegramOuterBoundarySandbox:
    """Records verify / setWebhook / deleteWebhook calls; optional failure injection."""

    telegram_bot_id: int = 888_001
    username: str = "e2e_provision_bot"
    verify_calls: list[str] = field(default_factory=list)
    set_webhook_calls: list[tuple[str, str, str]] = field(default_factory=list)
    delete_webhook_calls: list[str] = field(default_factory=list)
    reject_token_substring: str | None = None
    set_webhook_failures_before_success: int = 0
    force_set_webhook_failure: bool = False

    async def verify(self, token: str) -> TelegramBotVerificationResult:
        self.verify_calls.append(token)
        if self.reject_token_substring and self.reject_token_substring in token:
            raise TelegramTokenVerificationError("sandbox: invalid token")
        if len(token) < 10:
            raise TelegramTokenVerificationError("sandbox: token too short")
        return TelegramBotVerificationResult(
            telegram_bot_id=self.telegram_bot_id,
            username=self.username,
            first_name="E2E",
        )

    async def set_webhook(self, token: str, url: str, secret: str) -> None:
        self.set_webhook_calls.append((token, url, secret))
        if self.force_set_webhook_failure:
            raise TelegramBotApiError(TelegramApiErrorKind.WEBHOOK, "sandbox: forced setWebhook failure")
        if self.set_webhook_failures_before_success > 0:
            self.set_webhook_failures_before_success -= 1
            raise TelegramBotApiError(TelegramApiErrorKind.WEBHOOK, "sandbox: setWebhook failed")

    async def delete_webhook(self, token: str) -> None:
        self.delete_webhook_calls.append(token)


def install_telegram_outer_boundary_sandbox(
    monkeypatch: pytest.MonkeyPatch,
    sandbox: TelegramOuterBoundarySandbox,
) -> TelegramOuterBoundarySandbox:
    """Patch ``telegram_config_service`` module globals used by default service construction."""

    async def _verify(token: str) -> TelegramBotVerificationResult:
        return await sandbox.verify(token)

    async def _set(token: str, url: str, secret: str) -> None:
        await sandbox.set_webhook(token, url, secret)

    async def _delete(token: str) -> None:
        await sandbox.delete_webhook(token)

    monkeypatch.setattr(
        "app.services.telegram_config_service.http_verify_telegram_bot_token",
        _verify,
    )
    monkeypatch.setattr(
        "app.services.telegram_config_service.set_telegram_bot_webhook",
        _set,
    )
    monkeypatch.setattr(
        "app.services.telegram_config_service.delete_telegram_bot_webhook",
        _delete,
    )
    return sandbox


async def fetch_telegram_config_row_for_bot(
    db_url: str,
    bot_id: uuid.UUID,
) -> asyncpg.Record | None:
    conn = await asyncpg.connect(dsn=asyncpg_dsn(db_url))
    try:
        return await conn.fetchrow(
            """
            SELECT bot_token_encrypted, provisioning_status, is_connected, webhook_url,
                   webhook_secret_token_encrypted, metadata_json, last_verified_at
            FROM telegram_configs
            WHERE bot_id = $1
            """,
            bot_id,
        )
    finally:
        await conn.close()
