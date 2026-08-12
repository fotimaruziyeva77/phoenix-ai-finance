"""Unit tests for Telegram ``getMe`` verification (mocked HTTP)."""

from __future__ import annotations

import httpx
import pytest
from app.integrations.telegram_bot_verify import (
    TelegramTokenVerificationError,
    verify_telegram_bot_token_with_client,
)


@pytest.mark.asyncio
async def test_verify_getme_success_parses_identity() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/bot123456:TEST_TOKEN/getMe")
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "id": 987654321,
                    "is_bot": True,
                    "first_name": "Test",
                    "username": "my_test_bot",
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await verify_telegram_bot_token_with_client(client, "123456:TEST_TOKEN")
    assert result.telegram_bot_id == 987654321
    assert result.username == "my_test_bot"
    assert result.first_name == "Test"


@pytest.mark.asyncio
async def test_verify_ok_false_is_generic_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "description": "Unauthorized"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(TelegramTokenVerificationError) as excinfo:
            await verify_telegram_bot_token_with_client(client, "123:bad")
    msg = str(excinfo.value).lower()
    assert "unauthorized" not in msg
    assert "123:bad" not in msg


@pytest.mark.asyncio
async def test_verify_non_200_generic_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(TelegramTokenVerificationError):
            await verify_telegram_bot_token_with_client(client, "123:abc")


@pytest.mark.asyncio
async def test_verify_not_a_bot() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"ok": True, "result": {"id": 1, "is_bot": False}},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(TelegramTokenVerificationError):
            await verify_telegram_bot_token_with_client(client, "123:abc")


@pytest.mark.asyncio
async def test_verify_short_token() -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={"ok": True}))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(TelegramTokenVerificationError):
            await verify_telegram_bot_token_with_client(client, "short")
