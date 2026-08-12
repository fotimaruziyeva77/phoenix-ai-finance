"""
Telegram Bot API ``getMe`` verification (backward-compatible thin API).

Implementation delegates to :class:`~app.integrations.telegram_bot_api.client.TelegramBotApiClient`.
Do not log URLs or bodies that include the bot token.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.integrations.telegram_bot_api.client import TelegramBotApiClient
from app.integrations.telegram_bot_api.errors import TelegramApiErrorKind, TelegramBotApiError


@dataclass(frozen=True, slots=True)
class TelegramBotVerificationResult:
    """Subset of ``getMe`` useful for persistence (no raw token)."""

    telegram_bot_id: int
    username: str | None
    first_name: str | None


class TelegramTokenVerificationError(Exception):
    """Token invalid, Telegram unreachable, or unexpected API shape (safe message only)."""


def _map_api_error(exc: TelegramBotApiError) -> None:
    if exc.kind == TelegramApiErrorKind.TRANSPORT:
        raise TelegramTokenVerificationError(
            "Could not reach Telegram to verify the bot token.",
        ) from exc
    if exc.kind == TelegramApiErrorKind.INVALID_TOKEN:
        raise TelegramTokenVerificationError(exc.message) from exc
    raise TelegramTokenVerificationError(
        "Telegram returned an unexpected response.",
    ) from exc


async def verify_telegram_bot_token_with_client(
    client: httpx.AsyncClient,
    bot_api_token: str,
) -> TelegramBotVerificationResult:
    """
    Verify ``bot_api_token`` via ``getMe``.

    Raises:
        TelegramTokenVerificationError: Generic messages only (no token leakage).
    """
    api = TelegramBotApiClient(client)
    try:
        me = await api.get_me(bot_api_token)
    except TelegramBotApiError as exc:
        _map_api_error(exc)
    return TelegramBotVerificationResult(
        telegram_bot_id=me.bot_user_id,
        username=me.username,
        first_name=me.first_name,
    )


async def verify_telegram_bot_token(bot_api_token: str) -> TelegramBotVerificationResult:
    """Verify using a short-lived ``httpx.AsyncClient`` (timeouts enforced)."""
    token = (bot_api_token or "").strip()
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await verify_telegram_bot_token_with_client(client, token)
