"""
Backend tests for Telegram channel analytics hooks (:mod:`app.core.telegram_channel_events`).

Covers: message received/answered, lead-created (Telegram only), error and connect events, and
absence of secrets in recorded event payloads.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.telegram_channel_events import (
    TELEGRAM_CONNECT_FAILURE,
    TELEGRAM_CONNECT_SUCCESS,
    TELEGRAM_ERROR,
    TELEGRAM_LEAD_CREATED,
    TELEGRAM_MESSAGE_ANSWERED,
    TELEGRAM_MESSAGE_RECEIVED,
)
from app.integrations.telegram_bot_api.errors import TelegramApiErrorKind, TelegramBotApiError
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.repositories.lead_repository import LeadRepository
from app.schemas.ai_chat import SendBotMessageResult
from app.domain.telegram_channel_status import TELEGRAM_PROVISIONING_ACTIVE
from app.schemas.telegram_config import TelegramConfigRead
from app.services.sales_lead_capture_turn import run_sales_lead_capture_after_pipeline
from app.services.telegram_config_exceptions import TelegramTokenInvalidError
from app.services.telegram_config_service import TelegramConfigService
from app.services.telegram_webhook_inbound_service import TelegramWebhookInboundService

_FORBIDDEN_SECRET_MARKERS = (
    "123456789:AA_UNIT_TEST_BOT_TOKEN_NEVER_LOG",
    "webhook_secret_plaintext_xyz",
    "user_message_body_unique_string_q7k9",
)


def _assert_events_safe(events: list[dict[str, object]]) -> None:
    blob = str(events).lower()
    for s in _FORBIDDEN_SECRET_MARKERS:
        assert s.lower() not in blob, f"secret marker leaked into events: {s!r}"


def _recorder(monkeypatch: pytest.MonkeyPatch, module: str) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []

    def _capture(**kwargs: object) -> None:
        out.append(dict(kwargs))

    monkeypatch.setattr(f"{module}.emit_telegram_channel_event", _capture)
    return out


def _inbound_svc_with_loaded_bot(
    *,
    ai_result: SendBotMessageResult | None = None,
    send_side_effect: object | None = None,
) -> tuple[TelegramWebhookInboundService, MagicMock, uuid.UUID, uuid.UUID]:
    chat = MagicMock()
    chat.session = MagicMock()
    chat.merge_telegram_collected_hints = AsyncMock()

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

    users = MagicMock()
    users.get_by_id = AsyncMock(return_value=MagicMock(id=uuid.uuid4(), is_active=True))

    cfg = MagicMock()
    cfg.bot_token_encrypted = "enc-ciphertext-not-token"

    first = MagicMock()
    first.first = MagicMock(return_value=(cfg, bot))
    chat.session.execute = AsyncMock(return_value=first)

    ai = MagicMock()
    if ai_result is not None:
        ai.send_bot_message = AsyncMock(return_value=ai_result)
    else:
        ai.send_bot_message = AsyncMock()

    send_fn = AsyncMock(side_effect=send_side_effect)

    svc = TelegramWebhookInboundService(
        chat,
        users,
        ai,
        MagicMock(),
        send_telegram_text=send_fn,
        thread_service=threads,
    )
    return svc, chat, bot.id, conv.id


@pytest.mark.asyncio
async def test_telegram_analytics_inbound_message_received_and_answered_ordered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _capture(**kwargs: object) -> None:
        recorded.append(dict(kwargs))

    recorded: list[dict[str, object]] = []
    monkeypatch.setattr(
        "app.services.telegram_webhook_inbound_service.emit_telegram_channel_event",
        _capture,
    )

    ai_result = SendBotMessageResult(
        conversation_id=uuid.uuid4(),
        user_message_id=uuid.uuid4(),
        assistant_message_id=uuid.uuid4(),
        assistant_text=f"reply must not appear in logs {_FORBIDDEN_SECRET_MARKERS[2]}",
        success=True,
        error_code=None,
        latency_ms=5,
    )
    svc, _chat, bot_id, bound_conv_id = _inbound_svc_with_loaded_bot(ai_result=ai_result)

    plain = _FORBIDDEN_SECRET_MARKERS[0]
    monkeypatch.setattr(
        "app.services.telegram_webhook_inbound_service.decrypt_telegram_bot_token",
        lambda *_a, **_k: plain,
    )

    user_text = _FORBIDDEN_SECRET_MARKERS[2]
    await svc.handle_raw_update(
        bot_id=bot_id,
        raw_body=(
            b'{"update_id":42,"message":{"message_id":1,"chat":{"id":100,"type":"private"},'
            b'"text":"' + user_text.encode() + b'"}}'
        ),
    )

    kinds = [e.get("telegram_event") for e in recorded]
    assert kinds.count(TELEGRAM_MESSAGE_RECEIVED) == 1
    assert kinds.count(TELEGRAM_MESSAGE_ANSWERED) == 1
    assert kinds.index(TELEGRAM_MESSAGE_RECEIVED) < kinds.index(TELEGRAM_MESSAGE_ANSWERED)

    recv = next(e for e in recorded if e.get("telegram_event") == TELEGRAM_MESSAGE_RECEIVED)
    ans = next(e for e in recorded if e.get("telegram_event") == TELEGRAM_MESSAGE_ANSWERED)
    assert recv.get("inbound_chars") == len(user_text)
    assert str(recv.get("conversation_id")) == str(bound_conv_id)
    assert ans.get("ai_success") is True
    assert ans.get("outbound_sent") is True
    assert ans.get("outbound_chars") == len(ai_result.assistant_text.strip())
    _assert_events_safe(recorded)


@pytest.mark.asyncio
async def test_telegram_analytics_json_invalid_emits_error(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded = _recorder(monkeypatch, "app.services.telegram_webhook_inbound_service")
    svc, _, bot_id, _ = _inbound_svc_with_loaded_bot()
    monkeypatch.setattr(
        "app.services.telegram_webhook_inbound_service.decrypt_telegram_bot_token",
        lambda *_a, **_k: _FORBIDDEN_SECRET_MARKERS[0],
    )

    await svc.handle_raw_update(bot_id=bot_id, raw_body=b"not-json{")

    assert len(recorded) == 1
    assert recorded[0]["telegram_event"] == TELEGRAM_ERROR
    assert recorded[0]["error_code"] == "json_invalid"
    _assert_events_safe(recorded)


@pytest.mark.asyncio
async def test_telegram_analytics_parse_failed_emits_error(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded = _recorder(monkeypatch, "app.services.telegram_webhook_inbound_service")
    svc, _, bot_id, _ = _inbound_svc_with_loaded_bot()
    monkeypatch.setattr(
        "app.services.telegram_webhook_inbound_service.decrypt_telegram_bot_token",
        lambda *_a, **_k: _FORBIDDEN_SECRET_MARKERS[0],
    )

    await svc.handle_raw_update(bot_id=bot_id, raw_body=b'{"update_id":"bad"}')

    assert len(recorded) == 1
    assert recorded[0]["telegram_event"] == TELEGRAM_ERROR
    assert recorded[0]["error_code"] == "parse_failed"
    assert recorded[0].get("telegram_update_id") is None
    _assert_events_safe(recorded)


@pytest.mark.asyncio
async def test_telegram_analytics_outbound_send_failed_records_error_and_answered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded = _recorder(monkeypatch, "app.services.telegram_webhook_inbound_service")
    ai_result = SendBotMessageResult(
        conversation_id=uuid.uuid4(),
        user_message_id=uuid.uuid4(),
        assistant_message_id=uuid.uuid4(),
        assistant_text="ok",
        success=True,
        error_code=None,
        latency_ms=1,
    )
    svc, _, bot_id, _ = _inbound_svc_with_loaded_bot(
        ai_result=ai_result,
        send_side_effect=TelegramBotApiError(
            TelegramApiErrorKind.SEND_MESSAGE,
            "send failed",
        ),
    )
    monkeypatch.setattr(
        "app.services.telegram_webhook_inbound_service.decrypt_telegram_bot_token",
        lambda *_a, **_k: _FORBIDDEN_SECRET_MARKERS[0],
    )

    await svc.handle_raw_update(
        bot_id=bot_id,
        raw_body=b'{"update_id":7,"message":{"message_id":1,"chat":{"id":55,"type":"private"},"text":"x"}}',
    )

    kinds = [e.get("telegram_event") for e in recorded]
    assert TELEGRAM_MESSAGE_RECEIVED in kinds
    assert TELEGRAM_ERROR in kinds
    assert TELEGRAM_MESSAGE_ANSWERED in kinds
    err = next(e for e in recorded if e.get("telegram_event") == TELEGRAM_ERROR)
    assert err.get("error_code") == "outbound_send_failed"
    answered = next(e for e in recorded if e.get("telegram_event") == TELEGRAM_MESSAGE_ANSWERED)
    assert answered.get("outbound_sent") is False
    _assert_events_safe(recorded)


@pytest.mark.asyncio
async def test_telegram_analytics_inbound_unhandled_emits_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded = _recorder(monkeypatch, "app.services.telegram_webhook_inbound_service")
    svc, _, bot_id, _ = _inbound_svc_with_loaded_bot()
    svc._ai.send_bot_message = AsyncMock(side_effect=RuntimeError("internal"))  # type: ignore[method-assign]

    monkeypatch.setattr(
        "app.services.telegram_webhook_inbound_service.decrypt_telegram_bot_token",
        lambda *_a, **_k: _FORBIDDEN_SECRET_MARKERS[0],
    )

    await svc.handle_raw_update(
        bot_id=bot_id,
        raw_body=b'{"update_id":1,"message":{"message_id":1,"chat":{"id":9,"type":"private"},"text":"z"}}',
    )

    assert any(
        e.get("telegram_event") == TELEGRAM_ERROR and e.get("error_code") == "inbound_unhandled"
        for e in recorded
    )
    recv_before = [e for e in recorded if e.get("telegram_event") == TELEGRAM_MESSAGE_RECEIVED]
    assert len(recv_before) == 1
    _assert_events_safe(recorded)


@pytest.mark.asyncio
async def test_telegram_analytics_lead_created_when_channel_telegram(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded = _recorder(monkeypatch, "app.services.sales_lead_capture_turn")

    lead_id = uuid.uuid4()

    class _FakeCreation:
        def __init__(self, _repo: object) -> None:
            pass

        async def try_create_lead_from_conversation(self, **_kw: object) -> object:
            from app.services.lead_creation_service import LeadCreationResult

            return LeadCreationResult(
                created=True,
                lead=SimpleNamespace(id=lead_id),
                reason="created",
            )

    monkeypatch.setattr(
        "app.services.sales_lead_capture_turn.LeadCreationService",
        _FakeCreation,
    )

    oid = uuid.uuid4()
    bot = SimpleNamespace(
        id=uuid.uuid4(),
        owner_id=oid,
        goal_type="sales",
        niche_id="generic",
        name="Bot",
    )
    conv = SimpleNamespace(
        id=uuid.uuid4(),
        bot_id=bot.id,
        owner_id=oid,
        current_state="closing",
        niche_id_snapshot="generic",
        channel="telegram",
    )
    owner = SimpleNamespace(id=oid)
    collected: dict[str, object] = {
        "primary_need": _FORBIDDEN_SECRET_MARKERS[2],
        "phone": "+15551234567",
    }

    out = await run_sales_lead_capture_after_pipeline(
        lead_repo=MagicMock(spec=LeadRepository),
        bot=bot,
        owner_user=owner,
        conversation=conv,
        collected=collected,
        next_state=ConversationFlowState.closing,
        routing_intent=ConversationDetectedIntent.sales_interest,
        last_user_message="yes",
    )
    assert out.created_new_lead is True
    assert len(recorded) == 1
    assert recorded[0]["telegram_event"] == TELEGRAM_LEAD_CREATED
    assert str(recorded[0]["lead_id"]) == str(lead_id)
    assert str(recorded[0]["conversation_id"]) == str(conv.id)
    _assert_events_safe(recorded)


@pytest.mark.asyncio
async def test_telegram_analytics_lead_created_not_emitted_for_non_telegram_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded = _recorder(monkeypatch, "app.services.sales_lead_capture_turn")

    class _FakeCreation:
        def __init__(self, _repo: object) -> None:
            pass

        async def try_create_lead_from_conversation(self, **_kw: object) -> object:
            from app.services.lead_creation_service import LeadCreationResult

            return LeadCreationResult(
                created=True,
                lead=SimpleNamespace(id=uuid.uuid4()),
                reason="created",
            )

    monkeypatch.setattr(
        "app.services.sales_lead_capture_turn.LeadCreationService",
        _FakeCreation,
    )

    oid = uuid.uuid4()
    bot = SimpleNamespace(
        id=uuid.uuid4(),
        owner_id=oid,
        goal_type="sales",
        niche_id="generic",
        name="Bot",
    )
    conv = SimpleNamespace(
        id=uuid.uuid4(),
        bot_id=bot.id,
        owner_id=oid,
        current_state="closing",
        niche_id_snapshot="generic",
        channel="web_widget",
    )
    owner = SimpleNamespace(id=oid)
    collected: dict[str, object] = {"primary_need": "x", "phone": "+15551234567"}

    await run_sales_lead_capture_after_pipeline(
        lead_repo=MagicMock(spec=LeadRepository),
        bot=bot,
        owner_user=owner,
        conversation=conv,
        collected=collected,
        next_state=ConversationFlowState.closing,
        routing_intent=ConversationDetectedIntent.sales_interest,
        last_user_message="yes",
    )
    assert recorded == []


@pytest.mark.asyncio
async def test_telegram_analytics_connect_failure_emits_event(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded = _recorder(monkeypatch, "app.services.telegram_config_service")
    svc = TelegramConfigService(MagicMock(), MagicMock(), MagicMock())
    bid = uuid.uuid4()

    async def _boom(
        _self: object,
        _owner: object,
        _bot_id: uuid.UUID,
        _token: str,
    ) -> TelegramConfigRead:
        raise TelegramTokenInvalidError()

    monkeypatch.setattr(
        TelegramConfigService,
        "_connect_telegram_for_bot_impl",
        _boom,
    )

    owner = SimpleNamespace(id=uuid.uuid4())
    with pytest.raises(TelegramTokenInvalidError):
        await svc.connect_telegram_for_bot(owner, bid, "1234567890:" + "x" * 40)

    assert len(recorded) == 1
    assert recorded[0]["telegram_event"] == TELEGRAM_CONNECT_FAILURE
    assert recorded[0]["error_code"] == "telegram_token_invalid"
    assert str(recorded[0]["bot_id"]) == str(bid)
    _assert_events_safe(recorded)


@pytest.mark.asyncio
async def test_telegram_analytics_connect_success_emits_event(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded = _recorder(monkeypatch, "app.services.telegram_config_service")
    svc = TelegramConfigService(MagicMock(), MagicMock(), MagicMock())
    bid = uuid.uuid4()
    cfg_id = uuid.uuid4()
    now = datetime.now(UTC)

    read = TelegramConfigRead(
        id=cfg_id,
        bot_id=bid,
        owner_id=uuid.uuid4(),
        has_stored_bot_token=True,
        provisioning_status=TELEGRAM_PROVISIONING_ACTIVE,
        bot_username="mybot",
        webhook_url="https://api.example/public/telegram/webhook",
        is_connected=True,
        last_verified_at=now,
        metadata_json={"telegram_bot_id": 424242},
        created_at=now,
        updated_at=now,
    )

    async def _ok(
        _self: object,
        _owner: object,
        _bot_id: uuid.UUID,
        _token: str,
    ) -> TelegramConfigRead:
        return read

    monkeypatch.setattr(
        TelegramConfigService,
        "_connect_telegram_for_bot_impl",
        _ok,
    )

    owner = SimpleNamespace(id=uuid.uuid4())
    out = await svc.connect_telegram_for_bot(owner, bid, "1234567890:" + "y" * 40)
    assert out.id == cfg_id

    assert len(recorded) == 1
    assert recorded[0]["telegram_event"] == TELEGRAM_CONNECT_SUCCESS
    assert str(recorded[0]["telegram_config_id"]) == str(cfg_id)
    assert recorded[0]["telegram_bot_api_user_id"] == 424242
    assert "1234567890" not in str(recorded)
    _assert_events_safe(recorded)
