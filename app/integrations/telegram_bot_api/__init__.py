"""Reusable Telegram Bot API client (transport + parsing; no product logic)."""

from __future__ import annotations

from app.integrations.telegram_bot_api.client import TELEGRAM_API_ORIGIN, TelegramBotApiClient
from app.integrations.telegram_bot_api.errors import TelegramApiErrorKind, TelegramBotApiError
from app.integrations.telegram_bot_api.parse import parse_telegram_update
from app.integrations.telegram_bot_api.types import (
    ParsedTelegramUpdate,
    TelegramGetMeResult,
    TelegramSendMessageResult,
)

__all__ = [
    "TELEGRAM_API_ORIGIN",
    "ParsedTelegramUpdate",
    "TelegramApiErrorKind",
    "TelegramBotApiClient",
    "TelegramBotApiError",
    "TelegramGetMeResult",
    "TelegramSendMessageResult",
    "parse_telegram_update",
]
