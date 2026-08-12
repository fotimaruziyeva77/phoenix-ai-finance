"""Unit tests for Telegram inbound webhook helpers (no database)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.telegram_channel_events import (
    TELEGRAM_MESSAGE_ANSWERED,
    TELEGRAM_MESSAGE_RECEIVED,
)
from app.integrations.telegram_bot_api.types import ParsedTelegramUpdate
from app.integrations.telegram_bot_reply import TELEGRAM_MESSAGE_MAX_CHARS, truncate_for_telegram
from app.schemas.ai_chat import SendBotMessageResult
from app.services.ai_exceptions import AIServiceQuotaExceededError
from app.services.telegram_webhook_inbound_service import (
    TelegramWebhookInboundService,
    _extract_user_text_and_chat,
)


def test_extract_user_text_and_chat_message_ok() -> None:
    p = ParsedTelegramUpdate(
        update_id=1,
        raw_kind="message",
        message_text="  hello  ",
        chat_id=42,
    )
    assert _extract_user_text_and_chat(p) == ("hello", 42)


def test_extract_ignores_callback_and_unknown() -> None:
    assert _extract_user_text_and_chat(
        ParsedTelegramUpdate(1, "callback_query", None, 5),
    ) == (None, None)
    assert _extract_user_text_and_chat(
        ParsedTelegramUpdate(1, "unknown", None, None),
    ) == (None, None)


def test_extract_rejects_empty_text() -> None:
    assert _extract_user_text_and_chat(
        ParsedTelegramUpdate(1, "message", "   ", 1),
    ) == (None, None)


def test_truncate_for_telegram() -> None:
    long = "a" * (TELEGRAM_MESSAGE_MAX_CHARS + 10)
    out = truncate_for_telegram(long)
    assert len(out) == TELEGRAM_MESSAGE_MAX_CHARS
    assert out.endswith("…")


@pytest.mark.asyncio
async def test_handle_raw_update_swallows_ai_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inbound must not raise to the HTTP layer when AI fails."""
    chat = MagicMock()
    chat.session = MagicMock()
    chat.session.execute = AsyncMock()
    chat.merge_telegram_collected_hints = AsyncMock()

    users = MagicMock()
    users.get_by_id = AsyncMock(return_value=MagicMock(id=uuid.uuid4(), is_active=True))

    ai = MagicMock()
    ai.send_bot_message = AsyncMock(side_effect=RuntimeError("boom"))

    conv = MagicMock()
    conv.id = uuid.uuid4()
    threads = MagicMock()
    threads.get_or_create_telegram_thread = AsyncMock(return_value=conv)

    svc = TelegramWebhookInboundService(
        chat,
        users,
        ai,
        MagicMock(),
        send_telegram_text=AsyncMock(),
        thread_service=threads,
    )

    cfg = MagicMock()
    cfg.bot_token_encrypted = "enc"
    bot = MagicMock()
    bot.id = uuid.uuid4()
    bot.owner_id = uuid.uuid4()
    bot.niche_id = "education"
    bot.status = "active"
    bot.platform_suspended_at = None

    first = MagicMock()
    first.first = MagicMock(return_value=(cfg, bot))
    chat.session.execute = AsyncMock(return_value=first)

    monkeypatch.setattr(
        "app.services.telegram_webhook_inbound_service.decrypt_telegram_bot_token",
        lambda *_a, **_k: "1234567890:token_for_unit_test_only_xx",
    )

    await svc.handle_raw_update(
        bot_id=bot.id,
        raw_body=b'{"update_id":9,"message":{"message_id":1,"chat":{"id":99,"type":"private"},"text":"hi"}}',
    )

    chat.merge_telegram_collected_hints.assert_awaited_once()
    call_kw = chat.merge_telegram_collected_hints.await_args
    assert call_kw.args[0] == conv.id


@pytest.mark.asyncio
async def test_handle_raw_update_sends_generic_on_ai_service_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AIService.send_bot_message may raise (quota, validation); Telegram user still gets a reply."""
    send_mock = AsyncMock()

    chat = MagicMock()
    chat.session = MagicMock()
    chat.merge_telegram_collected_hints = AsyncMock()

    users = MagicMock()
    users.get_by_id = AsyncMock(return_value=MagicMock(id=uuid.uuid4(), is_active=True))

    conv = MagicMock()
    conv.id = uuid.uuid4()
    threads = MagicMock()
    threads.get_or_create_telegram_thread = AsyncMock(return_value=conv)

    ai = MagicMock()
    ai.send_bot_message = AsyncMock(side_effect=AIServiceQuotaExceededError("cap"))

    bot = MagicMock()
    bot.id = uuid.uuid4()
    bot.owner_id = uuid.uuid4()
    bot.niche_id = "education"
    bot.status = "active"
    bot.platform_suspended_at = None

    svc = TelegramWebhookInboundService(
        chat,
        users,
        ai,
        MagicMock(),
        send_telegram_text=send_mock,
        thread_service=threads,
    )

    cfg = MagicMock()
    cfg.bot_token_encrypted = "enc"
    first = MagicMock()
    first.first = MagicMock(return_value=(cfg, bot))
    chat.session.execute = AsyncMock(return_value=first)

    monkeypatch.setattr(
        "app.services.telegram_webhook_inbound_service.decrypt_telegram_bot_token",
        lambda *_a, **_k: "1234567890:token_for_unit_test_only_xx",
    )

    await svc.handle_raw_update(
        bot_id=bot.id,
        raw_body=b'{"update_id":9,"message":{"message_id":1,"chat":{"id":99,"type":"private"},"text":"hi"}}',
    )

    send_mock.assert_awaited()
    assert "Sorry" in (send_mock.await_args.kwargs.get("text") or "")


@pytest.mark.asyncio
async def test_handle_raw_update_emits_received_then_answered_no_token_in_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[dict[str, object]] = []

    def _recorder(**kwargs: object) -> None:
        recorded.append(dict(kwargs))

    monkeypatch.setattr(
        "app.services.telegram_webhook_inbound_service.emit_telegram_channel_event",
        _recorder,
    )

    chat = MagicMock()
    chat.session = MagicMock()
    chat.merge_telegram_collected_hints = AsyncMock()

    users = MagicMock()
    users.get_by_id = AsyncMock(return_value=MagicMock(id=uuid.uuid4(), is_active=True))

    conv = MagicMock()
    conv.id = uuid.uuid4()
    threads = MagicMock()
    threads.get_or_create_telegram_thread = AsyncMock(return_value=conv)

    bot = MagicMock()
    bot.id = uuid.uuid4()
    bot.owner_id = uuid.uuid4()
    bot.niche_id = "education"
    bot.status = "active"
    bot.platform_suspended_at = None

    ai = MagicMock()
    ai.send_bot_message = AsyncMock(
        return_value=SendBotMessageResult(
            conversation_id=conv.id,
            user_message_id=uuid.uuid4(),
            assistant_message_id=uuid.uuid4(),
            assistant_text="  hi back  ",
            success=True,
            error_code=None,
            latency_ms=10,
        ),
    )

    svc = TelegramWebhookInboundService(
        chat,
        users,
        ai,
        MagicMock(),
        send_telegram_text=AsyncMock(),
        thread_service=threads,
    )

    cfg = MagicMock()
    cfg.bot_token_encrypted = "enc"
    first = MagicMock()
    first.first = MagicMock(return_value=(cfg, bot))
    chat.session.execute = AsyncMock(return_value=first)

    secret_token = "1234567890:ABSOLUTE_UNIT_TEST_TOKEN_ONLY"
    monkeypatch.setattr(
        "app.services.telegram_webhook_inbound_service.decrypt_telegram_bot_token",
        lambda *_a, **_k: secret_token,
    )

    await svc.handle_raw_update(
        bot_id=bot.id,
        raw_body=b'{"update_id":9,"message":{"message_id":1,"chat":{"id":99,"type":"private"},"text":"hi"}}',
    )

    kinds = [r.get("telegram_event") for r in recorded]
    assert TELEGRAM_MESSAGE_RECEIVED in kinds
    assert TELEGRAM_MESSAGE_ANSWERED in kinds
    blob = str(recorded)
    assert secret_token not in blob
    assert "hi back" not in blob.lower()
    assert any(r.get("inbound_chars") == 2 for r in recorded)
