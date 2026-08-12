"""
Telegram ``setWebhook`` / ``deleteWebhook`` side effects (single integration layer).

``TelegramConfigService`` calls these after persistence decisions; tests may inject alternates.
"""

from __future__ import annotations

import httpx

from app.integrations.telegram_bot_api.client import TelegramBotApiClient

_TELEGRAM_WEBHOOK_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


async def set_telegram_bot_webhook(
    *,
    bot_token: str,
    webhook_https_url: str,
    secret_token: str,
    drop_pending_updates: bool = True,
) -> None:
    """Register webhook URL and optional ``secret_token`` with Telegram."""
    async with httpx.AsyncClient(timeout=_TELEGRAM_WEBHOOK_TIMEOUT) as client:
        api = TelegramBotApiClient(client)
        await api.set_webhook(
            bot_token,
            webhook_https_url,
            drop_pending_updates=drop_pending_updates,
            secret_token=secret_token,
        )


async def delete_telegram_bot_webhook(
    *,
    bot_token: str,
    drop_pending_updates: bool = True,
) -> None:
    """Remove webhook for the bot (best-effort before clearing local credentials)."""
    async with httpx.AsyncClient(timeout=_TELEGRAM_WEBHOOK_TIMEOUT) as client:
        api = TelegramBotApiClient(client)
        await api.delete_webhook(bot_token, drop_pending_updates=drop_pending_updates)
