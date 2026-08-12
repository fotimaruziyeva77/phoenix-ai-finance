"""Unit tests for :mod:`app.core.request_log_context` (no HTTP server)."""

from __future__ import annotations

import uuid

from app.core.request_log_context import (
    infer_path_log_context,
    parse_request_and_correlation_ids,
    w3c_trace_id_from_traceparent,
)
from app.lib.chat_channels import CONVERSATION_CHANNEL_TELEGRAM, CONVERSATION_CHANNEL_WEB_WIDGET
from starlette.requests import Request


def test_parse_request_and_correlation_ids_generates_when_missing() -> None:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "scheme": "http",
        "server": ("test", 80),
    }
    req = Request(scope)
    rid, cid = parse_request_and_correlation_ids(req)
    assert uuid.UUID(rid)
    assert cid == rid


def test_parse_request_and_correlation_ids_respects_headers() -> None:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [
            (b"x-request-id", b"req-1"),
            (b"x-correlation-id", b"corr-2"),
        ],
        "client": ("127.0.0.1", 1234),
        "scheme": "http",
        "server": ("test", 80),
    }
    req = Request(scope)
    rid, cid = parse_request_and_correlation_ids(req)
    assert rid == "req-1"
    assert cid == "corr-2"


def test_w3c_trace_id_from_traceparent_valid() -> None:
    tid = "0af7651916cd43dd8448eb211c80319c"
    tp = f"00-{tid}-00f067aa0ba902b7-01"
    assert w3c_trace_id_from_traceparent(tp) == tid


def test_w3c_trace_id_from_traceparent_invalid() -> None:
    assert w3c_trace_id_from_traceparent(None) is None
    assert w3c_trace_id_from_traceparent("") is None
    assert w3c_trace_id_from_traceparent("not-a-traceparent") is None


def test_infer_path_log_context_widget_and_telegram() -> None:
    bid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    w = infer_path_log_context("/api/v1/public/widget/somekey/chat")
    assert w.get("channel") == CONVERSATION_CHANNEL_WEB_WIDGET
    assert "bot_id" not in w

    t = infer_path_log_context(f"/api/v1/public/telegram/{bid}/webhook")
    assert t.get("channel") == CONVERSATION_CHANNEL_TELEGRAM
    assert t.get("bot_id") == bid

    o = infer_path_log_context(f"/api/v1/bots/{bid}/conversations")
    assert o.get("bot_id") == bid
