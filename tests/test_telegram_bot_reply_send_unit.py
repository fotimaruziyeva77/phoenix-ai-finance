"""
Send-path tests for :mod:`app.integrations.telegram_bot_reply` with mocked Bot API client.

Ensures formatting + truncation run before ``sendMessage`` and the HTTP layer never sees raw leaks.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from app.integrations.telegram_bot_api.client import TelegramBotApiClient
from app.integrations.telegram_bot_api.types import TelegramSendMessageResult
from app.integrations.telegram_bot_reply import (
    TELEGRAM_MESSAGE_MAX_CHARS,
    send_telegram_text_to_chat,
    truncate_for_telegram,
)


@pytest.mark.asyncio
async def test_send_passes_formatted_trimmed_text_to_send_message(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[tuple[str, int, str]] = []

    async def fake_send_message(
        self: TelegramBotApiClient,
        token: str,
        chat_id: int,
        text: str,
        *,
        disable_web_page_preview: bool = True,
    ) -> TelegramSendMessageResult:
        captured.append((token, chat_id, text))
        assert disable_web_page_preview is True
        return TelegramSendMessageResult(message_id=1, chat_id=chat_id)

    monkeypatch.setattr(TelegramBotApiClient, "send_message", fake_send_message)

    with patch("app.integrations.telegram_bot_reply.httpx.AsyncClient"):
        await send_telegram_text_to_chat(
            bot_token="SECRET_TOKEN",
            chat_id=4242,
            text="  Hello.\n\n\nSecond.  ",
        )

    assert len(captured) == 1
    token, cid, payload = captured[0]
    assert token == "SECRET_TOKEN"
    assert cid == 4242
    assert payload == "Hello.\n\nSecond."
    assert "SECRET_TOKEN" not in payload


@pytest.mark.asyncio
async def test_send_strips_internal_markers_before_api(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []

    async def fake_send_message(
        self: TelegramBotApiClient,
        token: str,
        chat_id: int,
        text: str,
        *,
        disable_web_page_preview: bool = True,
    ) -> TelegramSendMessageResult:
        captured.append(text)
        return TelegramSendMessageResult(message_id=1, chat_id=chat_id)

    monkeypatch.setattr(TelegramBotApiClient, "send_message", fake_send_message)

    with patch("app.integrations.telegram_bot_reply.httpx.AsyncClient"):
        await send_telegram_text_to_chat(
            bot_token="t",
            chat_id=1,
            text="Visible\n__lead_capture_done: true\nAlso visible",
        )

    assert len(captured) == 1
    assert "Visible" in captured[0] and "Also visible" in captured[0]
    assert "__lead_capture" not in captured[0]


@pytest.mark.asyncio
async def test_send_final_payload_never_exceeds_telegram_hard_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []

    async def fake_send_message(
        self: TelegramBotApiClient,
        token: str,
        chat_id: int,
        text: str,
        *,
        disable_web_page_preview: bool = True,
    ) -> TelegramSendMessageResult:
        captured.append(text)
        return TelegramSendMessageResult(message_id=1, chat_id=chat_id)

    monkeypatch.setattr(TelegramBotApiClient, "send_message", fake_send_message)

    huge = "Q" * 20_000
    with patch("app.integrations.telegram_bot_reply.httpx.AsyncClient"):
        await send_telegram_text_to_chat(bot_token="t", chat_id=1, text=huge)

    assert len(captured) == 1
    assert len(captured[0]) <= TELEGRAM_MESSAGE_MAX_CHARS


@pytest.mark.asyncio
async def test_send_skips_api_when_format_produces_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_send = AsyncMock(return_value=TelegramSendMessageResult(message_id=1, chat_id=1))
    monkeypatch.setattr(TelegramBotApiClient, "send_message", mock_send)

    with patch("app.integrations.telegram_bot_reply.httpx.AsyncClient"):
        await send_telegram_text_to_chat(bot_token="t", chat_id=1, text="   \n\x00  ")

    mock_send.assert_not_called()


def test_truncate_for_telegram_special_chars_intact_until_cap() -> None:
    """Hard truncate must not corrupt markup-like chars (still plain text)."""
    base = "<item>*bold*_test`"
    long = base * 500
    out = truncate_for_telegram(long, max_chars=TELEGRAM_MESSAGE_MAX_CHARS)
    assert len(out) == TELEGRAM_MESSAGE_MAX_CHARS
    assert out.endswith("…")
