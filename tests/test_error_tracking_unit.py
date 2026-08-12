"""Tests for :mod:`app.core.error_tracking` — config modes, init, capture, and scrubbing (no network)."""

from __future__ import annotations

import sys
import types
import uuid
from unittest.mock import MagicMock

import pytest
from app.core import error_tracking as et
from app.core.config import Settings


@pytest.fixture
def mock_sentry_sdk_module(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """
    Provide a fake ``sentry_sdk`` so tests run without ``pip install sentry-sdk``.

    :mod:`app.core.error_tracking` imports ``sentry_sdk`` inside functions, so this must be
    registered before those code paths run.
    """
    mod = types.ModuleType("sentry_sdk")
    mod.init = MagicMock()
    mod.capture_exception = MagicMock()
    mod.capture_message = MagicMock()
    mod.flush = MagicMock()

    scope = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=scope)
    cm.__exit__ = MagicMock(return_value=False)
    mod.push_scope = MagicMock(return_value=cm)
    mod.Hub = MagicMock()

    monkeypatch.setitem(sys.modules, "sentry_sdk", mod)
    return mod


@pytest.fixture(autouse=True)
def _reset_error_tracking_initialized() -> None:
    """``init_error_tracking`` is process-global; isolate tests from each other and from other modules."""
    et._initialized = False
    yield
    et._initialized = False


def test_error_tracking_inactive_without_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.delenv("APP_SENTRY_DSN", raising=False)
    s = Settings(
        error_tracking_enabled=True,
        error_tracking_sentry_dsn=None,
    )
    assert et.error_tracking_is_active(s) is False


def test_error_tracking_active_with_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    s = Settings(
        error_tracking_enabled=True,
        error_tracking_sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
    )
    assert et.error_tracking_is_active(s) is True


def test_error_tracking_disabled_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    s = Settings(
        error_tracking_enabled=False,
        error_tracking_sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
    )
    assert et.error_tracking_is_active(s) is False


def test_init_clean_no_config_does_not_touch_sentry(
    monkeypatch: pytest.MonkeyPatch,
    mock_sentry_sdk_module: types.ModuleType,
) -> None:
    s = Settings(
        error_tracking_enabled=True,
        error_tracking_sentry_dsn=None,
        environment="local",
    )
    et.init_error_tracking(s)
    mock_sentry_sdk_module.init.assert_not_called()


def test_init_clean_when_configured_calls_sentry_with_safe_defaults(
    mock_sentry_sdk_module: types.ModuleType,
) -> None:
    dsn = "https://examplePublicKey@o0.ingest.sentry.io/0"
    s = Settings(
        error_tracking_enabled=True,
        error_tracking_sentry_dsn=dsn,
        environment="local",
        app_version="1.2.3",
        error_tracking_traces_sample_rate=0.0,
        error_tracking_release=None,
    )
    et.init_error_tracking(s)
    mock_sentry_sdk_module.init.assert_called_once()
    kwargs = mock_sentry_sdk_module.init.call_args.kwargs
    assert kwargs["dsn"] == dsn
    assert kwargs["environment"] == "local"
    assert kwargs["release"] == "1.2.3"
    assert kwargs["send_default_pii"] is False
    assert kwargs["traces_sample_rate"] == 0.0
    assert kwargs["default_integrations"] is False
    assert kwargs["integrations"] == []
    assert kwargs["before_send"] is et._before_send_sentry


def test_init_idempotent_second_call_noops(mock_sentry_sdk_module: types.ModuleType) -> None:
    s = Settings(
        error_tracking_enabled=True,
        error_tracking_sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
    )
    et.init_error_tracking(s)
    et.init_error_tracking(s)
    assert mock_sentry_sdk_module.init.call_count == 1


def test_capture_noops_when_inactive(monkeypatch: pytest.MonkeyPatch, mock_sentry_sdk_module: types.ModuleType) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.setattr(et, "error_tracking_is_active", lambda settings=None: False)
    et.capture_exception(RuntimeError("x"), domain="test", tags={"a": "b"})
    et.capture_message("hello", domain="test")
    et.report_ai_provider_turn_failure(
        success=False,
        provider_name="p",
        provider_error_code="rate_limited",
        ai_category=None,
        conversation_id=str(uuid.uuid4()),
        bot_id=str(uuid.uuid4()),
    )
    et.report_server_mapped_error(
        request=None,
        domain="auth",
        status_code=503,
        code="x",
        exc=RuntimeError("y"),
    )
    mock_sentry_sdk_module.capture_exception.assert_not_called()
    mock_sentry_sdk_module.capture_message.assert_not_called()


def test_capture_exception_invokes_sentry_when_active(
    mock_sentry_sdk_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(et, "error_tracking_is_active", lambda settings=None: True)
    err = ValueError("unit_test_capture")
    et.capture_exception(err, domain="integration_test", tags={"k": "v"})
    mock_sentry_sdk_module.capture_exception.assert_called_once_with(err)
    scope = mock_sentry_sdk_module.push_scope.return_value.__enter__.return_value
    scope.set_tag.assert_any_call("domain", "integration_test")
    scope.set_tag.assert_any_call("k", "v")


def test_capture_message_invokes_sentry_when_active(
    mock_sentry_sdk_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(et, "error_tracking_is_active", lambda settings=None: True)
    et.capture_message("hello_sentry", domain="msg_test", level="warning")
    mock_sentry_sdk_module.capture_message.assert_called_once()
    assert mock_sentry_sdk_module.capture_message.call_args[0][0] == "hello_sentry"
    assert mock_sentry_sdk_module.capture_message.call_args[1].get("level") == "warning"


def test_report_ai_provider_turn_failure_uses_abstraction(
    mock_sentry_sdk_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(et, "error_tracking_is_active", lambda settings=None: True)
    et.report_ai_provider_turn_failure(
        success=False,
        provider_name="test_provider",
        provider_error_code="timeout",
        ai_category="timeout",
        conversation_id=str(uuid.uuid4()),
        bot_id=str(uuid.uuid4()),
        channel="web_widget",
    )
    mock_sentry_sdk_module.capture_message.assert_called_once()
    msg = mock_sentry_sdk_module.capture_message.call_args[0][0]
    assert "ai_provider_failure" in msg
    assert "timeout" in msg


def test_shutdown_error_tracking_flushes_sentry(mock_sentry_sdk_module: types.ModuleType) -> None:
    et.shutdown_error_tracking(timeout=0.01)
    mock_sentry_sdk_module.flush.assert_called_once_with(timeout=0.01)


def test_before_send_strips_request_secrets_and_query_string() -> None:
    event = {
        "request": {
            "url": "https://api.example.com/path?token=secret&x=1",
            "headers": {"Authorization": "Bearer x"},
            "cookies": {"session": "abc"},
            "data": {"password": "nope"},
            "query_string": "token=leak",
        },
        "extra": {"nested": {"api_key": "k"}},
    }
    out = et._before_send_sentry(event, {})
    assert out is not None
    req = out.get("request") or {}
    assert "headers" not in req
    assert "cookies" not in req
    assert "data" not in req
    assert "query_string" not in req
    url = req.get("url", "")
    assert "?" not in url
    assert "token=secret" not in url
    nested = (out.get("extra") or {}).get("nested") or {}
    assert nested.get("api_key") == "[redacted]"


def test_scrub_value_redacts_sensitive_keys() -> None:
    raw = {
        "ok": "safe",
        "nested": {"refresh_token": "rt", "public": 1},
        "list": [{"Authorization": "bad"}],
    }
    out = et._scrub_value(raw)
    assert out["ok"] == "safe"
    assert out["nested"]["refresh_token"] == "[redacted]"
    assert out["nested"]["public"] == 1
    assert out["list"][0]["Authorization"] == "[redacted]"


def test_safe_request_context_no_secrets() -> None:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "POST",
        "path": "/api/v1/bots",
        "raw_path": b"/api/v1/bots",
        "query_string": b"token=should_not_appear",
        "headers": [
            (b"authorization", b"Bearer supersecret"),
            (b"cookie", b"session=abc"),
        ],
        "client": ("127.0.0.1", 1),
        "scheme": "http",
        "server": ("test", 80),
        "state": {},
    }
    from starlette.requests import Request

    req = Request(scope)
    req.state.request_id = "rid-1"
    req.state.correlation_id = "cid-2"
    ctx = et._safe_request_context(req)
    assert ctx["method"] == "POST"
    assert ctx["path"] == "/api/v1/bots"
    assert ctx["request_id"] == "rid-1"
    assert ctx["correlation_id"] == "cid-2"
    assert ctx.get("w3c_trace_id") is None
    req.state.w3c_trace_id = "a" * 32
    ctx2 = et._safe_request_context(req)
    assert ctx2.get("w3c_trace_id") == "a" * 32
    blob = str(ctx).lower()
    assert "supersecret" not in blob
    assert "bearer" not in blob
    assert "cookie" not in blob
