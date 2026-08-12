"""
Mocked HTTP tests for :mod:`app.integrations.telegram_bot_api` (no real Telegram).

Checklist:
  1. Token verification path (``getMe``) — success and invalid-token mapping.
  2. Webhook set/delete — correct endpoints and JSON bodies; failures as ``WEBHOOK`` kind.
  3. ``send_message`` — request shape and ``TelegramSendMessageResult`` normalization.
  4. Invalid / error Telegram responses map to ``TelegramBotApiError`` kinds (no description leak).
  5. ``parse_telegram_update`` / ``client.parse_update`` — message, edited, callback, unknown, JSON string.
"""

from __future__ import annotations

import json

import httpx
import pytest
from app.integrations.telegram_bot_api import (
    TelegramApiErrorKind,
    TelegramBotApiClient,
    TelegramBotApiError,
    parse_telegram_update,
)


@pytest.mark.asyncio
async def test_get_me_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url).endswith("/bot1234567890:T/getMe")
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "id": 42,
                    "is_bot": True,
                    "username": "the_bot",
                    "first_name": "The",
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        api = TelegramBotApiClient(http)
        me = await api.get_me("1234567890:T")
    assert me.bot_user_id == 42
    assert me.username == "the_bot"


@pytest.mark.asyncio
async def test_get_me_ok_false_invalid_token() -> None:
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, json={"ok": False, "description": "Unauthorized"}),
    )
    async with httpx.AsyncClient(transport=transport) as http:
        api = TelegramBotApiClient(http)
        with pytest.raises(TelegramBotApiError) as ei:
            await api.get_me("1234567890:OKFALSE")
    assert ei.value.kind == TelegramApiErrorKind.INVALID_TOKEN
    assert "unauthorized" not in ei.value.message.lower()


@pytest.mark.asyncio
async def test_set_webhook_empty_url() -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={"ok": True}))
    async with httpx.AsyncClient(transport=transport) as http:
        api = TelegramBotApiClient(http)
        with pytest.raises(TelegramBotApiError) as ei:
            await api.set_webhook("1234567890:x", "  ")
    assert ei.value.kind == TelegramApiErrorKind.WEBHOOK


@pytest.mark.asyncio
async def test_set_webhook_failure_kind() -> None:
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, json={"ok": False, "description": "Bad URL"}),
    )
    async with httpx.AsyncClient(transport=transport) as http:
        api = TelegramBotApiClient(http)
        with pytest.raises(TelegramBotApiError) as ei:
            await api.set_webhook("1234567890:x", "https://example.com/hook")
    assert ei.value.kind == TelegramApiErrorKind.WEBHOOK
    assert "bad url" not in ei.value.message.lower()


@pytest.mark.asyncio
async def test_delete_webhook_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url).endswith("/bot1234567890:x/deleteWebhook")
        assert json.loads(request.content.decode()) == {}
        return httpx.Response(200, json={"ok": True, "result": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        api = TelegramBotApiClient(http)
        await api.delete_webhook("1234567890:x")


@pytest.mark.asyncio
async def test_set_webhook_posts_secret_token_when_provided() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body["url"] == "https://example.com/hook"
        assert body["secret_token"] == "ab-cd_01"
        return httpx.Response(200, json={"ok": True, "result": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        api = TelegramBotApiClient(http)
        await api.set_webhook("1234567890:x", "https://example.com/hook", secret_token="ab-cd_01")


@pytest.mark.asyncio
async def test_set_webhook_success_posts_url_and_drop_pending() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url).endswith("/bot1234567890:x/setWebhook")
        body = json.loads(request.content.decode())
        assert body["url"] == "https://example.com/hook"
        assert body["drop_pending_updates"] is True
        return httpx.Response(200, json={"ok": True, "result": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        api = TelegramBotApiClient(http)
        await api.set_webhook(
            "1234567890:x",
            "https://example.com/hook",
            drop_pending_updates=True,
        )


@pytest.mark.asyncio
async def test_delete_webhook_drop_pending_in_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content.decode()) == {"drop_pending_updates": True}
        return httpx.Response(200, json={"ok": True, "result": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        api = TelegramBotApiClient(http)
        await api.delete_webhook("1234567890:x", drop_pending_updates=True)


@pytest.mark.asyncio
async def test_delete_webhook_false_result_raises_webhook_kind() -> None:
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, json={"ok": True, "result": False}),
    )
    async with httpx.AsyncClient(transport=transport) as http:
        api = TelegramBotApiClient(http)
        with pytest.raises(TelegramBotApiError) as ei:
            await api.delete_webhook("1234567890:x")
    assert ei.value.kind == TelegramApiErrorKind.WEBHOOK


@pytest.mark.asyncio
async def test_send_message_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body["chat_id"] == 99
        assert body["text"] == "hi"
        return httpx.Response(
            200,
            json={"ok": True, "result": {"message_id": 7, "chat": {"id": 99, "type": "private"}}},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        api = TelegramBotApiClient(http)
        out = await api.send_message("1234567890:x", 99, "hi")
    assert out.message_id == 7
    assert out.chat_id == 99


@pytest.mark.asyncio
async def test_send_message_normalizes_disable_preview_default_true() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body["disable_web_page_preview"] is True
        return httpx.Response(
            200,
            json={"ok": True, "result": {"message_id": 1, "chat": {"id": 2, "type": "private"}}},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        api = TelegramBotApiClient(http)
        await api.send_message("1234567890:x", 2, "x")

    def handler_false(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body["disable_web_page_preview"] is False
        return httpx.Response(
            200,
            json={"ok": True, "result": {"message_id": 1, "chat": {"id": 2, "type": "private"}}},
        )

    transport2 = httpx.MockTransport(handler_false)
    async with httpx.AsyncClient(transport=transport2) as http:
        api = TelegramBotApiClient(http)
        await api.send_message("1234567890:x", 2, "x", disable_web_page_preview=False)


@pytest.mark.asyncio
async def test_get_me_http_502_maps_transport_kind() -> None:
    transport = httpx.MockTransport(
        lambda r: httpx.Response(502, json={"ok": False, "description": "Bad Gateway"}),
    )
    async with httpx.AsyncClient(transport=transport) as http:
        api = TelegramBotApiClient(http)
        with pytest.raises(TelegramBotApiError) as ei:
            await api.get_me("1234567890:x")
    assert ei.value.kind == TelegramApiErrorKind.TRANSPORT
    assert "bad gateway" not in ei.value.message.lower()


@pytest.mark.asyncio
async def test_send_message_ok_false() -> None:
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, json={"ok": False, "description": "Forbidden"}),
    )
    async with httpx.AsyncClient(transport=transport) as http:
        api = TelegramBotApiClient(http)
        with pytest.raises(TelegramBotApiError) as ei:
            await api.send_message("1234567890:x", 1, "x")
    assert ei.value.kind == TelegramApiErrorKind.SEND_MESSAGE


def test_parse_update_from_json_string() -> None:
    raw = json.dumps(
        {
            "update_id": 9,
            "message": {"message_id": 1, "chat": {"id": 2, "type": "private"}, "text": "from str"},
        },
    )
    u = parse_telegram_update(raw)
    assert u.update_id == 9
    assert u.message_text == "from str"


def test_parse_update_edited_message() -> None:
    u = parse_telegram_update(
        {
            "update_id": 1,
            "edited_message": {
                "message_id": 2,
                "chat": {"id": 3, "type": "private"},
                "text": "edited",
            },
        },
    )
    assert u.raw_kind == "edited_message"
    assert u.message_text == "edited"
    assert u.chat_id == 3


def test_parse_update_callback_query() -> None:
    u = parse_telegram_update(
        {
            "update_id": 1,
            "callback_query": {
                "id": "cb1",
                "from": {"id": 10, "is_bot": False, "first_name": "U"},
                "message": {"message_id": 2, "chat": {"id": 5, "type": "private"}},
                "data": "act:1",
            },
        },
    )
    assert u.raw_kind == "callback_query"
    assert u.chat_id == 5
    assert u.message_text == "act:1"


def test_parse_update_business_message() -> None:
    u = parse_telegram_update(
        {
            "update_id": 501,
            "business_message": {
                "message_id": 1,
                "chat": {"id": 55, "type": "private"},
                "text": "biz hi",
                "from": {"id": 1, "is_bot": False, "first_name": "A"},
            },
        },
    )
    assert u.update_id == 501
    assert u.raw_kind == "business_message"
    assert u.message_text == "biz hi"
    assert u.chat_id == 55


def test_parse_update_unknown_shape() -> None:
    u = parse_telegram_update({"update_id": 99, "channel_post": {"message_id": 1}})
    assert u.update_id == 99
    assert u.raw_kind == "unknown"
    assert u.chat_id is None


def test_parse_update_message_caption_only() -> None:
    u = parse_telegram_update(
        {
            "update_id": 7,
            "message": {
                "message_id": 1,
                "chat": {"id": 99, "type": "private"},
                "photo": [],
                "caption": "hello via caption",
            },
        },
    )
    assert u.raw_kind == "message"
    assert u.message_text == "hello via caption"
    assert u.chat_id == 99


def test_parse_update_message() -> None:
    u = parse_telegram_update(
        {
            "update_id": 1,
            "message": {
                "message_id": 2,
                "chat": {"id": 3, "type": "private"},
                "text": "hello",
                "from": {"id": 9, "is_bot": False, "first_name": "Pat", "username": "pat_tg"},
            },
        },
    )
    assert u.update_id == 1
    assert u.raw_kind == "message"
    assert u.message_text == "hello"
    assert u.chat_id == 3
    assert u.from_user_username == "pat_tg"
    assert u.from_user_first_name == "Pat"


def test_parse_update_invalid_json_string() -> None:
    with pytest.raises(TelegramBotApiError) as ei:
        parse_telegram_update("{not json")
    assert ei.value.kind == TelegramApiErrorKind.PARSE


def test_parse_update_missing_update_id() -> None:
    with pytest.raises(TelegramBotApiError) as ei:
        parse_telegram_update({"message": {}})
    assert ei.value.kind == TelegramApiErrorKind.PARSE


@pytest.mark.asyncio
async def test_client_parse_update_delegates() -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={"ok": True}))
    async with httpx.AsyncClient(transport=transport) as http:
        api = TelegramBotApiClient(http)
        u = api.parse_update({"update_id": 5, "message": {"chat": {"id": 1}, "text": "a"}})
    assert u.update_id == 5
