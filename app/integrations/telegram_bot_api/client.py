"""
Async Telegram Bot API client (transport only — no dashboard or sales logic).

Inject a configured ``httpx.AsyncClient`` for timeouts and tests. Never log request URLs
(contain the bot token) or raw error bodies from Telegram.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.integrations.telegram_bot_api.errors import (
    TelegramApiErrorKind,
    TelegramBotApiError,
    map_telegram_http_or_api_failure,
)
from app.integrations.telegram_bot_api.parse import parse_telegram_update
from app.integrations.telegram_bot_api.types import (
    ParsedTelegramUpdate,
    TelegramGetMeResult,
    TelegramSendMessageResult,
)

TELEGRAM_API_ORIGIN = "https://api.telegram.org"


class TelegramBotApiClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    def parse_update(self, payload: object) -> ParsedTelegramUpdate:
        """Parse webhook JSON (dict or JSON string) into a narrow update view."""
        return parse_telegram_update(payload)

    def _url(self, token: str, method: str) -> str:
        return f"{TELEGRAM_API_ORIGIN}/bot{token}/{method}"

    def _validate_token(self, token: str) -> str:
        t = (token or "").strip()
        if len(t) < 10:
            raise TelegramBotApiError(
                TelegramApiErrorKind.INVALID_TOKEN,
                "Telegram did not accept this bot token.",
            )
        return t

    async def _get_api(self, token: str, method: str) -> dict[str, Any] | bool | list[Any]:
        t = self._validate_token(token)
        url = self._url(t, method)
        try:
            response = await self._http.get(url)
        except httpx.RequestError as exc:
            raise TelegramBotApiError(
                TelegramApiErrorKind.TRANSPORT,
                "Could not reach Telegram.",
            ) from exc
        return self._interpret_response(response, method)

    async def _post_api(
        self,
        token: str,
        method: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | bool | list[Any]:
        t = self._validate_token(token)
        url = self._url(t, method)
        try:
            response = await self._http.post(url, json=json_body or {})
        except httpx.RequestError as exc:
            raise TelegramBotApiError(
                TelegramApiErrorKind.TRANSPORT,
                "Could not reach Telegram.",
            ) from exc
        return self._interpret_response(response, method)

    def _interpret_response(
        self,
        response: httpx.Response,
        method: str,
    ) -> dict[str, Any] | bool | list[Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise TelegramBotApiError(
                TelegramApiErrorKind.UNEXPECTED,
                "Telegram returned an unexpected response.",
            ) from exc

        if not isinstance(payload, dict):
            raise TelegramBotApiError(
                TelegramApiErrorKind.UNEXPECTED,
                "Telegram returned an unexpected response.",
            )

        ok = payload.get("ok")
        if response.status_code != 200 or ok is not True:
            kind, msg = map_telegram_http_or_api_failure(
                method_name=method,
                status_code=response.status_code,
                ok=ok if isinstance(ok, bool) else None,
            )
            raise TelegramBotApiError(kind, msg)

        result = payload.get("result")
        if result is None:
            raise TelegramBotApiError(
                TelegramApiErrorKind.UNEXPECTED,
                "Telegram returned an unexpected response.",
            )
        if isinstance(result, (dict, list, bool)):
            return result
        raise TelegramBotApiError(
            TelegramApiErrorKind.UNEXPECTED,
            "Telegram returned an unexpected response.",
        )

    async def get_me(self, token: str) -> TelegramGetMeResult:
        """Call ``getMe`` for the bot token (metadata + token validity)."""
        raw = await self._get_api(token, "getMe")
        if not isinstance(raw, dict):
            raise TelegramBotApiError(
                TelegramApiErrorKind.UNEXPECTED,
                "Telegram returned an unexpected response.",
            )
        tid = raw.get("id")
        if not isinstance(tid, int):
            raise TelegramBotApiError(
                TelegramApiErrorKind.UNEXPECTED,
                "Telegram returned an unexpected response.",
            )
        is_bot = raw.get("is_bot")
        if is_bot is not True:
            raise TelegramBotApiError(
                TelegramApiErrorKind.INVALID_TOKEN,
                "Telegram did not accept this bot token.",
            )
        un = raw.get("username")
        fn = raw.get("first_name")
        return TelegramGetMeResult(
            bot_user_id=tid,
            is_bot=True,
            username=un if isinstance(un, str) else None,
            first_name=fn if isinstance(fn, str) else None,
        )

    async def set_webhook(
        self,
        token: str,
        webhook_url: str,
        *,
        drop_pending_updates: bool = False,
        secret_token: str | None = None,
    ) -> None:
        """Register ``webhook_url`` (HTTPS) for this bot."""
        w = webhook_url.strip()
        if not w:
            raise TelegramBotApiError(
                TelegramApiErrorKind.WEBHOOK,
                "Webhook URL is empty.",
            )
        body: dict[str, Any] = {"url": w}
        if drop_pending_updates:
            body["drop_pending_updates"] = True
        if secret_token is not None:
            st = secret_token.strip()
            if st:
                body["secret_token"] = st
        result = await self._post_api(token, "setWebhook", body)
        if result is not True:
            raise TelegramBotApiError(
                TelegramApiErrorKind.WEBHOOK,
                "Telegram webhook request failed.",
            )

    async def delete_webhook(self, token: str, *, drop_pending_updates: bool = False) -> None:
        """Remove the bot webhook."""
        body: dict[str, Any] = {}
        if drop_pending_updates:
            body["drop_pending_updates"] = True
        result = await self._post_api(token, "deleteWebhook", body if body else None)
        if result is not True:
            raise TelegramBotApiError(
                TelegramApiErrorKind.WEBHOOK,
                "Telegram webhook request failed.",
            )

    async def send_message(
        self,
        token: str,
        chat_id: int,
        text: str,
        *,
        disable_web_page_preview: bool = True,
    ) -> TelegramSendMessageResult:
        """Send a plain text message to ``chat_id``."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
        }
        raw = await self._post_api(token, "sendMessage", payload)
        if not isinstance(raw, dict):
            raise TelegramBotApiError(
                TelegramApiErrorKind.SEND_MESSAGE,
                "Telegram could not send the message.",
            )
        mid = raw.get("message_id")
        chat = raw.get("chat")
        cid = chat.get("id") if isinstance(chat, dict) else None
        if not isinstance(mid, int) or not isinstance(cid, int):
            raise TelegramBotApiError(
                TelegramApiErrorKind.SEND_MESSAGE,
                "Telegram could not send the message.",
            )
        return TelegramSendMessageResult(message_id=mid, chat_id=cid)
