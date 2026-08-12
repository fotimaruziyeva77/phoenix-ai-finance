"""
Focused tests for public widget channel analytics hooks (structured logs, no sensitive leakage).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.deps import rate_limit_public_widget_bootstrap, rate_limit_public_widget_chat
from app.core.limiters.outcome import RateLimitOutcome
from app.core.public_widget_abuse import (
    enforce_public_widget_chat_turn,
    widget_key_digest,
)
from app.core.public_widget_channel_events import (
    WIDGET_BOOTSTRAP_LOADED,
    WIDGET_ERROR,
    WIDGET_MESSAGE_ANSWERED,
    WIDGET_MESSAGE_RECEIVED,
    WIDGET_THROTTLED,
    emit_public_widget_channel_event,
)
from app.lib.widget_origin_policy import WidgetOriginPolicyOptions
from app.schemas.ai_chat import SendBotMessageResult
from app.schemas.public_widget_chat import PublicWidgetChatRequest
from app.services.public_widget_chat_service import PublicWidgetChatService
from app.services.widget_bootstrap_exceptions import WidgetBootstrapOriginForbiddenError
from app.services.widget_bootstrap_service import WidgetBootstrapService
from fastapi import HTTPException, Request


def _capture_emit(monkeypatch: pytest.MonkeyPatch, target_module: str) -> list[dict]:
    out: list[dict] = []

    def _recorder(**kwargs: object) -> None:
        out.append(dict(kwargs))

    monkeypatch.setattr(f"{target_module}.emit_public_widget_channel_event", _recorder)
    return out


def _assert_no_sensitive_leak(blob: object, *, forbidden_substrings: tuple[str, ...]) -> None:
    text = str(blob).lower()
    for s in forbidden_substrings:
        assert s.lower() not in text, f"leaked forbidden substring {s!r}"


@pytest.mark.asyncio
async def test_bootstrap_records_widget_bootstrap_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_emit(monkeypatch, "app.services.widget_bootstrap_service")
    bot_id = uuid.uuid4()
    wc_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    wc = SimpleNamespace(
        id=wc_id,
        bot_id=bot_id,
        allowed_domains_json=[],
        is_enabled=True,
        welcome_text=None,
        theme=None,
    )
    bot = SimpleNamespace(
        id=bot_id,
        name="Analytics Bot",
        owner_id=owner_id,
        platform_suspended_at=None,
    )
    secret_pk = "pk_live_super_secret_widget_token_abc"

    monkeypatch.setattr(
        "app.services.widget_bootstrap_service.load_widget_and_bot_by_public_key",
        AsyncMock(return_value=(wc, bot)),
    )
    monkeypatch.setattr(
        "app.services.widget_bootstrap_service.enforce_public_widget_origin_and_enabled",
        lambda *_a, **_kw: None,
    )

    session = MagicMock()
    session.get = AsyncMock(return_value=SimpleNamespace(is_active=True))
    svc = WidgetBootstrapService(session, origin_policy=WidgetOriginPolicyOptions())
    await svc.get_bootstrap(
        public_widget_key=secret_pk,
        origin_header="https://allowed.example",
        referer_header=None,
    )

    assert len(captured) == 1
    ev = captured[0]
    assert ev["event"] == WIDGET_BOOTSTRAP_LOADED
    assert str(ev["bot_id"]) == str(bot_id)
    assert str(ev["widget_config_id"]) == str(wc_id)
    assert ev["widget_key_digest"] == widget_key_digest(secret_pk)
    assert len(ev["widget_key_digest"]) == 16
    _assert_no_sensitive_leak(captured, forbidden_substrings=(secret_pk,))


@pytest.mark.asyncio
async def test_chat_records_received_then_answered(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_emit(monkeypatch, "app.services.public_widget_chat_service")
    bot_id = uuid.uuid4()
    wc_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    wc = SimpleNamespace(
        id=wc_id,
        bot_id=bot_id,
        allowed_domains_json=[],
        is_enabled=True,
        welcome_text=None,
        theme=None,
    )
    bot = SimpleNamespace(
        id=bot_id,
        name="Chat Bot",
        owner_id=owner_id,
        platform_suspended_at=None,
    )
    secret_pk = "pk_chat_secret_xyz"
    visitor_key = "v" * 20
    visitor_message = "my private visitor question about health"

    monkeypatch.setattr(
        "app.services.public_widget_chat_service.load_widget_and_bot_by_public_key",
        AsyncMock(return_value=(wc, bot)),
    )
    monkeypatch.setattr(
        "app.services.public_widget_chat_service.enforce_public_widget_origin_and_enabled",
        lambda *_a, **_kw: None,
    )

    chat_repo = MagicMock()
    chat_repo.session = MagicMock()
    bot_repo = MagicMock()
    user_repo = MagicMock()
    user_repo.get_by_id = AsyncMock(return_value=SimpleNamespace(id=owner_id, is_active=True))
    ai = MagicMock()
    um = uuid.uuid4()
    am = uuid.uuid4()
    ai.send_bot_message = AsyncMock(
        return_value=SendBotMessageResult(
            conversation_id=conv_id,
            user_message_id=um,
            assistant_message_id=am,
            assistant_text="reply",
            success=True,
            latency_ms=42,
        ),
    )

    svc = PublicWidgetChatService(
        chat_repo=chat_repo,
        bot_repo=bot_repo,
        user_repo=user_repo,
        ai_service=ai,
        origin_policy=WidgetOriginPolicyOptions(),
    )
    sessions = MagicMock()
    sessions.get_or_create_conversation = AsyncMock(return_value=(SimpleNamespace(id=conv_id), visitor_key))
    svc._widget_sessions = sessions

    body = PublicWidgetChatRequest(message=visitor_message, visitor_session_key=visitor_key)
    await svc.send_public_message(
        public_widget_key=secret_pk,
        origin_header="https://allowed.example",
        referer_header=None,
        body=body,
    )

    assert len(captured) == 2
    recv, ans = captured
    assert recv["event"] == WIDGET_MESSAGE_RECEIVED
    assert ans["event"] == WIDGET_MESSAGE_ANSWERED
    assert recv["inbound_chars"] == len(visitor_message)
    assert ans["inbound_chars"] == len(visitor_message)
    assert ans["latency_ms"] == 42
    assert recv["visitor_session_digest"] is not None
    assert len(recv["visitor_session_digest"]) == 12
    _assert_no_sensitive_leak(
        captured,
        forbidden_substrings=(secret_pk, visitor_key, visitor_message, "private", "health"),
    )
    for row in captured:
        assert "message" not in row
        assert "assistant_text" not in row


@pytest.mark.asyncio
async def test_rate_limit_chat_emits_widget_throttled(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_emit(monkeypatch, "app.api.deps")

    class _Limiter:
        async def consume(self, *_a, **_kw) -> RateLimitOutcome:
            return RateLimitOutcome(allowed=False, retry_after_seconds=30)

    monkeypatch.setattr("app.api.deps.client_ip", lambda *_a, **_kw: "203.0.113.1")

    settings = MagicMock()
    settings.rate_limiting_enabled = True
    settings.rate_limit_public_widget_chat_per_minute = 5
    settings.trust_forwarded_for = False
    settings.rate_limit_public_fail_open_on_redis_error = True

    request = MagicMock(spec=Request)
    pk = "pk_rate_test_12345"

    with pytest.raises(HTTPException) as ei:
        await rate_limit_public_widget_chat(request, settings, pk, limiter=_Limiter())
    assert ei.value.status_code == 429

    assert len(captured) == 1
    assert captured[0]["event"] == WIDGET_THROTTLED
    assert captured[0]["throttle_kind"] == "rate_limit_chat"
    assert captured[0]["widget_key_digest"] == widget_key_digest(pk)
    _assert_no_sensitive_leak(captured, forbidden_substrings=(pk,))


@pytest.mark.asyncio
async def test_rate_limit_bootstrap_emits_widget_throttled(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_emit(monkeypatch, "app.api.deps")

    class _Limiter:
        async def consume(self, *_a, **_kw) -> RateLimitOutcome:
            return RateLimitOutcome(allowed=False, retry_after_seconds=30)

    monkeypatch.setattr("app.api.deps.client_ip", lambda *_a, **_kw: "203.0.113.2")

    settings = MagicMock()
    settings.rate_limiting_enabled = True
    settings.rate_limit_public_widget_bootstrap_per_minute = 3
    settings.trust_forwarded_for = False
    settings.rate_limit_public_fail_open_on_redis_error = True

    request = MagicMock(spec=Request)
    pk = "pk_boot_rate_67890"

    with pytest.raises(HTTPException) as ei:
        await rate_limit_public_widget_bootstrap(request, settings, pk, limiter=_Limiter())
    assert ei.value.status_code == 429

    assert len(captured) == 1
    assert captured[0]["event"] == WIDGET_THROTTLED
    assert captured[0]["throttle_kind"] == "rate_limit_bootstrap"
    _assert_no_sensitive_leak(captured, forbidden_substrings=(pk,))


@pytest.mark.asyncio
async def test_abuse_message_too_long_emits_widget_throttled(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_emit(monkeypatch, "app.core.public_widget_abuse")

    settings = MagicMock()
    settings.rate_limiting_enabled = True
    settings.public_widget_abuse_enabled = True
    settings.public_widget_abuse_max_message_chars = 10
    settings.public_widget_abuse_session_burst_per_minute = 0
    settings.public_widget_abuse_identical_total_per_window = 0
    settings.public_widget_abuse_identical_window_seconds = 300.0
    settings.public_widget_abuse_max_consecutive_identical = 0
    settings.trust_forwarded_for = False

    request = MagicMock(spec=Request)
    pk = "pk_abuse_long_key"

    monkeypatch.setattr("app.core.public_widget_abuse.client_ip", lambda *_a, **_kw: "198.51.100.1")

    with pytest.raises(HTTPException) as ei:
        await enforce_public_widget_chat_turn(
            request=request,
            settings=settings,
            public_widget_key=pk,
            message_text="x" * 50,
            visitor_session_key=None,
            limiter=MagicMock(),
        )
    assert ei.value.status_code == 400

    assert len(captured) == 1
    assert captured[0]["event"] == WIDGET_THROTTLED
    assert captured[0]["throttle_kind"] == "abuse_message_too_long"
    _assert_no_sensitive_leak(captured, forbidden_substrings=(pk, "xxxx"))


def test_emit_uses_widget_event_key_for_structlog_not_event_kwarg_collision() -> None:
    """structlog reserves ``event`` for the log message; payload uses ``widget_event``."""
    with patch("app.core.public_widget_channel_events._LOG") as log_mock:
        emit_public_widget_channel_event(
            event=WIDGET_BOOTSTRAP_LOADED,
            bot_id=uuid.uuid4(),
            widget_key_digest="a" * 16,
        )
        log_mock.info.assert_called_once()
        args, kwargs = log_mock.info.call_args
        assert args[0] == "public_widget_channel_event"
        assert kwargs["widget_event"] == WIDGET_BOOTSTRAP_LOADED
        assert kwargs["channel"] == "web_widget"
        assert "event" not in kwargs or kwargs.get("event") != WIDGET_BOOTSTRAP_LOADED


@pytest.mark.asyncio
async def test_bootstrap_error_handler_emits_widget_error_without_raw_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.exception_handlers import widget_bootstrap_error_handler

    captured = _capture_emit(monkeypatch, "app.core.exception_handlers")
    raw_key = "leak_me_not_public_widget_key"
    req = MagicMock(spec=Request)
    req.url.path = f"/api/v1/public/widget/{raw_key}/bootstrap"

    await widget_bootstrap_error_handler(req, WidgetBootstrapOriginForbiddenError())

    assert len(captured) == 1
    ev = captured[0]
    assert ev["event"] == WIDGET_ERROR
    assert ev["error_code"] == "widget_origin_forbidden"
    assert ev["http_status"] == 403
    assert ev["widget_key_digest"] == widget_key_digest(raw_key)
    _assert_no_sensitive_leak(captured, forbidden_substrings=(raw_key,))
