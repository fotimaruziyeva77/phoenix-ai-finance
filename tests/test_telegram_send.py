"""Tests for :mod:`app.integrations.telegram.telegram_send`."""

from __future__ import annotations

import asyncio

import httpx
from app.integrations.telegram.lead_alert_types import TelegramSendTarget
from app.integrations.telegram.telegram_send import send_telegram_text_message


def test_send_success_200_ok_true() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json={"ok": True, "result": {}})

    transport = httpx.MockTransport(handler)
    target = TelegramSendTarget(bot_token="TESTTOKEN", chat_id="12345")

    async def run() -> None:
        async with httpx.AsyncClient(transport=transport) as client:
            out = await send_telegram_text_message(target, "hi", client=client)
        assert out.ok is True
        assert out.attempts == 1
        assert out.error_kind is None
        assert len(calls) == 1
        assert "TESTTOKEN" in calls[0]
        assert "sendMessage" in calls[0]

    asyncio.run(run())


def test_send_retries_then_succeeds_on_500() -> None:
    responses = iter(
        [
            httpx.Response(500, json={}),
            httpx.Response(200, json={"ok": True}),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    transport = httpx.MockTransport(handler)
    target = TelegramSendTarget(bot_token="T", chat_id="1")

    async def run() -> None:
        async with httpx.AsyncClient(transport=transport) as client:
            out = await send_telegram_text_message(target, "x", client=client)
        assert out.ok is True
        assert out.attempts == 2

    asyncio.run(run())


def test_send_no_retry_on_400() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"ok": False})

    transport = httpx.MockTransport(handler)
    target = TelegramSendTarget(bot_token="T", chat_id="1")

    async def run() -> None:
        async with httpx.AsyncClient(transport=transport) as client:
            out = await send_telegram_text_message(target, "x", client=client)
        assert out.ok is False
        assert out.attempts == 1
        assert out.error_kind == "http_400"

    asyncio.run(run())


def test_send_telegram_ok_false_200() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "description": "Bad Request: chat not found"})

    transport = httpx.MockTransport(handler)
    target = TelegramSendTarget(bot_token="T", chat_id="1")

    async def run() -> None:
        async with httpx.AsyncClient(transport=transport) as client:
            out = await send_telegram_text_message(target, "x", client=client)
        assert out.ok is False
        assert out.error_kind == "telegram_api_error"

    asyncio.run(run())
