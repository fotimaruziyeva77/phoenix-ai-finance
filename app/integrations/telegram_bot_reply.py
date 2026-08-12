"""Outbound Telegram Bot API text replies (webhook follow-up)."""

from __future__ import annotations

import httpx

from app.integrations.telegram_bot_api.client import TelegramBotApiClient
from app.integrations.telegram_reply_format import format_telegram_bot_reply_text

TELEGRAM_MESSAGE_MAX_CHARS = 4096

_TELEGRAM_HTTP_TIMEOUT = httpx.Timeout(20.0, connect=5.0)


def truncate_for_telegram(text: str, *, max_chars: int = TELEGRAM_MESSAGE_MAX_CHARS) -> str:
    t = (text or "").strip()
    if len(t) <= max_chars:
        return t
    if max_chars <= 1:
        return t[:max_chars]
    return t[: max_chars - 1] + "…"


async def send_telegram_text_to_chat(*, bot_token: str, chat_id: int, text: str) -> None:
    """
    Send a plain text message via ``sendMessage`` (no ``parse_mode``).

    Text is passed through :func:`~app.integrations.telegram_reply_format.format_telegram_bot_reply_text`
    before the Telegram hard length cap — keeps AI generation decoupled from channel presentation.
    """
    payload = truncate_for_telegram(format_telegram_bot_reply_text(text))
    if not payload:
        return
    async with httpx.AsyncClient(timeout=_TELEGRAM_HTTP_TIMEOUT) as client:
        api = TelegramBotApiClient(client)
        await api.send_message(bot_token, chat_id, payload)
