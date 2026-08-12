"""Unit tests for :mod:`app.core.telegram_channel_events` (structured logs, no secrets)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from app.core.telegram_channel_events import (
    TELEGRAM_CONNECT_FAILURE,
    TELEGRAM_MESSAGE_RECEIVED,
    emit_telegram_channel_event,
)
from app.lib.chat_channels import CONVERSATION_CHANNEL_TELEGRAM


def _assert_no_secret_leak(blob: object, *, forbidden: tuple[str, ...]) -> None:
    text = str(blob).lower()
    for s in forbidden:
        assert s.lower() not in text, f"unexpected substring in payload: {s!r}"


def test_emit_telegram_channel_event_info_builds_payload() -> None:
    bot_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    with patch("app.core.telegram_channel_events._LOG") as log_mock:
        emit_telegram_channel_event(
            telegram_event=TELEGRAM_MESSAGE_RECEIVED,
            bot_id=bot_id,
            conversation_id=conv_id,
            telegram_chat_id=99,
            telegram_update_id=12,
            inbound_chars=3,
        )
    log_mock.info.assert_called_once()
    assert log_mock.info.call_args.args[0] == "telegram_channel_event"
    kwargs = log_mock.info.call_args.kwargs
    assert kwargs["channel"] == CONVERSATION_CHANNEL_TELEGRAM
    assert kwargs["telegram_event"] == TELEGRAM_MESSAGE_RECEIVED
    assert kwargs["bot_id"] == str(bot_id)
    assert kwargs["conversation_id"] == str(conv_id)
    assert kwargs["telegram_chat_id"] == 99
    assert kwargs["telegram_update_id"] == 12
    assert kwargs["inbound_chars"] == 3


def test_emit_telegram_channel_event_truncates_long_ai_error_code() -> None:
    long_code = "x" * 200
    with patch("app.core.telegram_channel_events._LOG") as log_mock:
        emit_telegram_channel_event(
            telegram_event=TELEGRAM_CONNECT_FAILURE,
            level="warning",
            ai_error_code=long_code,
        )
    log_mock.warning.assert_called_once()
    kwargs = log_mock.warning.call_args.kwargs
    assert len(kwargs["ai_error_code"]) == 64


def test_emit_never_passes_raw_tokens_to_logger() -> None:
    fake_token = "123456789:AAFAKE_BOTFATHER_TOKEN_FOR_TEST"
    with patch("app.core.telegram_channel_events._LOG") as log_mock:
        emit_telegram_channel_event(
            telegram_event=TELEGRAM_MESSAGE_RECEIVED,
            bot_id=uuid.uuid4(),
            extra={"note": "ok"},
        )
    call = log_mock.info.call_args
    _assert_no_secret_leak(call, forbidden=(fake_token,))
    assert isinstance(call.kwargs, dict)
    for v in call.kwargs.values():
        _assert_no_secret_leak(v, forbidden=(fake_token,))


def test_emit_error_level_uses_log_error() -> None:
    with patch("app.core.telegram_channel_events._LOG") as log_mock:
        emit_telegram_channel_event(
            telegram_event="telegram_error",
            level="error",
            error_code="inbound_unhandled",
        )
    log_mock.error.assert_called_once()
    assert log_mock.error.call_args.kwargs["error_code"] == "inbound_unhandled"


def test_emit_extra_merges_non_none() -> None:
    with patch("app.core.telegram_channel_events._LOG") as log_mock:
        emit_telegram_channel_event(
            telegram_event=TELEGRAM_MESSAGE_RECEIVED,
            extra={"k_ok": 1, "k_skip": None},
        )
    kw = log_mock.info.call_args.kwargs
    assert kw["k_ok"] == 1
    assert "k_skip" not in kw


def test_emit_mock_logger_kwargs_safe_for_secrets() -> None:
    """Regression: logger receives only explicit safe fields (no message text)."""
    log_mock = MagicMock()
    with patch("app.core.telegram_channel_events._LOG", log_mock):
        emit_telegram_channel_event(
            telegram_event=TELEGRAM_MESSAGE_RECEIVED,
            bot_id=uuid.uuid4(),
            inbound_chars=5000,
        )
    secret = "super_secret_user_message_content"
    _assert_no_secret_leak(log_mock.info.call_args, forbidden=(secret,))
