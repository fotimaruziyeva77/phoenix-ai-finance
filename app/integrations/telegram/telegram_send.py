"""Minimal Telegram Bot API sendMessage with bounded retries (httpx)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from app.integrations.telegram.lead_alert_types import TelegramSendTarget

_TELEGRAM_API_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
_MAX_ATTEMPTS = 3
_BACKOFF_BASE_S = 0.4


@dataclass(frozen=True, slots=True)
class TelegramSendOutcome:
    """Structured result — safe to log (no secrets)."""

    ok: bool
    attempts: int
    last_status_code: int | None
    error_kind: str | None


def _should_retry_http_status(code: int) -> bool:
    return code == 429 or code >= 500


async def send_telegram_text_message(
    target: TelegramSendTarget,
    text: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> TelegramSendOutcome:
    """
    POST sendMessage. Retries on timeouts, connection errors, HTTP 429, and HTTP 5xx.

    Does not log ``bot_token`` or ``chat_id``.
    """
    url = f"https://api.telegram.org/bot{target.bot_token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": target.chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    own_client = client is None
    cli = client or httpx.AsyncClient(timeout=_TELEGRAM_API_TIMEOUT)
    last_code: int | None = None
    try:
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                resp = await cli.post(url, json=payload)
                last_code = resp.status_code
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok") is True:
                        return TelegramSendOutcome(
                            ok=True,
                            attempts=attempt,
                            last_status_code=200,
                            error_kind=None,
                        )
                    return TelegramSendOutcome(
                        ok=False,
                        attempts=attempt,
                        last_status_code=200,
                        error_kind="telegram_api_error",
                    )
                if _should_retry_http_status(resp.status_code) and attempt < _MAX_ATTEMPTS:
                    await asyncio.sleep(_BACKOFF_BASE_S * (2 ** (attempt - 1)))
                    continue
                return TelegramSendOutcome(
                    ok=False,
                    attempts=attempt,
                    last_status_code=resp.status_code,
                    error_kind=f"http_{resp.status_code}",
                )
            except httpx.TimeoutException:
                if attempt < _MAX_ATTEMPTS:
                    await asyncio.sleep(_BACKOFF_BASE_S * (2 ** (attempt - 1)))
                    continue
                return TelegramSendOutcome(
                    ok=False,
                    attempts=attempt,
                    last_status_code=last_code,
                    error_kind="timeout",
                )
            except httpx.RequestError:
                if attempt < _MAX_ATTEMPTS:
                    await asyncio.sleep(_BACKOFF_BASE_S * (2 ** (attempt - 1)))
                    continue
                return TelegramSendOutcome(
                    ok=False,
                    attempts=attempt,
                    last_status_code=last_code,
                    error_kind="request_error",
                )
        return TelegramSendOutcome(
            ok=False,
            attempts=_MAX_ATTEMPTS,
            last_status_code=last_code,
            error_kind="exhausted",
        )
    finally:
        if own_client:
            await cli.aclose()
