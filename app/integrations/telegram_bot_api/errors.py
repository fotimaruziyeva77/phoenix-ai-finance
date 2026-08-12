"""
Normalized errors for Telegram Bot API calls.

Messages are safe for logs and JSON (no tokens, chat ids, or Telegram ``description`` text).
"""

from __future__ import annotations

from enum import StrEnum


class TelegramApiErrorKind(StrEnum):
    INVALID_TOKEN = "invalid_token"
    WEBHOOK = "webhook"
    SEND_MESSAGE = "send_message"
    PARSE = "parse"
    TRANSPORT = "transport"
    UNEXPECTED = "unexpected"


class TelegramBotApiError(Exception):
    """Base for all Telegram Bot API client failures."""

    def __init__(self, kind: TelegramApiErrorKind, message: str) -> None:
        self.kind = kind
        self.message = message
        super().__init__(message)


def map_telegram_http_or_api_failure(
    *,
    method_name: str,
    status_code: int,
    ok: bool | None,
) -> tuple[TelegramApiErrorKind, str]:
    """
    Choose (kind, safe_message) for non-success responses.

    ``method_name`` is the Telegram method suffix only (e.g. ``getMe``) — never include the token.
    """
    if status_code >= 500:
        return TelegramApiErrorKind.TRANSPORT, "Could not reach Telegram."
    if status_code != 200:
        if method_name == "getMe":
            return TelegramApiErrorKind.INVALID_TOKEN, "Telegram did not accept this bot token."
        if method_name in ("setWebhook", "deleteWebhook"):
            return TelegramApiErrorKind.WEBHOOK, "Telegram webhook request failed."
        if method_name == "sendMessage":
            return TelegramApiErrorKind.SEND_MESSAGE, "Telegram could not send the message."
        return TelegramApiErrorKind.UNEXPECTED, "Telegram returned an unexpected response."
    if ok is False:
        if method_name == "getMe":
            return TelegramApiErrorKind.INVALID_TOKEN, "Telegram did not accept this bot token."
        if method_name in ("setWebhook", "deleteWebhook"):
            return TelegramApiErrorKind.WEBHOOK, "Telegram webhook request failed."
        if method_name == "sendMessage":
            return TelegramApiErrorKind.SEND_MESSAGE, "Telegram could not send the message."
        return TelegramApiErrorKind.UNEXPECTED, "Telegram returned an unexpected response."
    return TelegramApiErrorKind.UNEXPECTED, "Telegram returned an unexpected response."
