"""
Integration tests: request/correlation IDs, structured HTTP logs, and safe metadata.

Uses JSON logging written to an in-memory :class:`io.StringIO` attached to the root
:class:`logging.StreamHandler` so logs from :class:`fastapi.testclient.TestClient`'s
background thread are captured reliably (``capsys`` is not thread-safe with Starlette's client).
"""

from __future__ import annotations

import io
import json
import logging
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from app.core.config import get_settings
from app.lib.chat_channels import CONVERSATION_CHANNEL_WEB_WIDGET
from app.main import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient

_DISTINCTIVE_SECRET = "bfai_test_token_DO_NOT_LOG_9f3c2a1e"


def _reset_root_logging() -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.WARNING)


def _attach_json_log_stream() -> io.StringIO:
    """After :func:`create_app` configures logging, send root StreamHandler output here."""
    stream = io.StringIO()
    root = logging.getLogger()
    for h in root.handlers:
        if isinstance(h, logging.StreamHandler):
            if hasattr(h, "setStream"):
                h.setStream(stream)
            else:
                h.stream = stream
    return stream


def _json_log_payloads(raw: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _http_request_events(payloads: list[dict[str, Any]], *, http_event: str) -> list[dict[str, Any]]:
    return [
        p
        for p in payloads
        if p.get("event") == "http_request" and p.get("http_event") == http_event
    ]


@pytest.fixture
def json_log_app(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[FastAPI, io.StringIO]]:
    """Fresh app with JSON logs to a StringIO buffer; clears settings cache around the test."""
    monkeypatch.setenv("APP_LOG_JSON", "true")
    monkeypatch.setenv("APP_LOG_LEVEL", "INFO")
    monkeypatch.setenv("APP_SERVICE_NAME", "logging-integration")
    monkeypatch.setenv("APP_ENVIRONMENT", "pytest-logs")
    get_settings.cache_clear()
    _reset_root_logging()

    app = create_app()
    stream = _attach_json_log_stream()

    async def _boom() -> None:
        raise RuntimeError("logging_test_intentional_boom")

    app.add_api_route(
        "/__test_logging_boom",
        _boom,
        methods=["GET"],
        include_in_schema=False,
    )

    try:
        yield app, stream
    finally:
        get_settings.cache_clear()
        _reset_root_logging()


@pytest.fixture
def logging_client(json_log_app: tuple[FastAPI, io.StringIO]) -> Iterator[tuple[TestClient, io.StringIO]]:
    app, stream = json_log_app
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, stream


def test_request_and_correlation_ids_generated_and_propagated(logging_client) -> None:
    client, stream = logging_client
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

    rid = r.headers.get("X-Request-ID") or r.headers.get("x-request-id")
    cid = r.headers.get("X-Correlation-ID") or r.headers.get("x-correlation-id")
    assert rid, "expected X-Request-ID on response"
    assert cid, "expected X-Correlation-ID on response"
    uuid.UUID(str(rid))  # generated ids are UUIDs
    assert cid == rid

    payloads = _json_log_payloads(stream.getvalue())
    completed = _http_request_events(payloads, http_event="completed")
    assert completed, f"expected http_request completed log, got events: {[p.get('event') for p in payloads]}"
    last = completed[-1]
    assert last.get("request_id") == rid
    assert last.get("correlation_id") == cid
    assert last.get("http_status") == 200
    assert last.get("http_method") == "GET"
    assert "/health" in (last.get("http_path") or "")
    assert last.get("http_route") is not None
    assert last.get("service") == "logging-integration"
    assert last.get("environment") == "pytest-logs"
    assert "timestamp" in last
    lvl = last.get("level")
    assert lvl is None or str(lvl).lower() in ("info", "information", "debug")


def test_inbound_request_and_correlation_headers_echoed(logging_client) -> None:
    client, stream = logging_client
    r = client.get(
        "/api/v1/health",
        headers={
            "X-Request-ID": "client-req-7",
            "X-Correlation-ID": "client-corr-8",
        },
    )
    assert r.status_code == 200
    assert (r.headers.get("X-Request-ID") or r.headers.get("x-request-id")) == "client-req-7"
    assert (r.headers.get("X-Correlation-ID") or r.headers.get("x-correlation-id")) == "client-corr-8"

    payloads = _json_log_payloads(stream.getvalue())
    completed = _http_request_events(payloads, http_event="completed")[-1]
    assert completed.get("request_id") == "client-req-7"
    assert completed.get("correlation_id") == "client-corr-8"


def test_logs_include_safe_path_metadata_for_bot_path(logging_client) -> None:
    client, stream = logging_client
    bid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    r = client.get(f"/api/v1/bots/{bid}")
    assert r.status_code == 401

    out = stream.getvalue()
    assert _DISTINCTIVE_SECRET not in out
    payloads = _json_log_payloads(out)
    completed = _http_request_events(payloads, http_event="completed")[-1]
    assert completed.get("bot_id") == bid
    assert completed.get("user_id") in (None, "")
    assert completed.get("http_status") == 401


def test_authorization_bearer_not_logged(logging_client) -> None:
    client, stream = logging_client
    client.get(
        "/api/v1/health",
        headers={"Authorization": f"Bearer {_DISTINCTIVE_SECRET}"},
    )
    out = stream.getvalue()
    assert _DISTINCTIVE_SECRET not in out


def test_middleware_failure_log_then_handling(logging_client) -> None:
    client, stream = logging_client
    r = client.get("/__test_logging_boom")
    assert r.status_code == 500

    out = stream.getvalue()
    assert _DISTINCTIVE_SECRET not in out

    payloads = _json_log_payloads(out)
    failed = _http_request_events(payloads, http_event="failed")
    assert failed, "expected middleware http_request failed on exception"
    fail_line = failed[-1]
    assert fail_line.get("request_id")
    assert fail_line.get("correlation_id")
    assert fail_line.get("http_path") == "/__test_logging_boom"
    assert "duration_ms" in fail_line

    unhandled = [p for p in payloads if p.get("event") == "unhandled_exception"]
    assert unhandled, "expected unhandled_exception log for 500 path"
    u = unhandled[-1]
    assert u.get("request_id")
    assert u.get("correlation_id") is not None
    assert u.get("path") == "/__test_logging_boom"
    assert u.get("method") == "GET"
    exc_blob = u.get("exception") or ""
    assert "logging_test_intentional_boom" in str(exc_blob)


def test_client_error_uses_warning_http_log(logging_client) -> None:
    client, stream = logging_client
    r = client.get("/api/v1/bots")
    assert r.status_code == 401
    payloads = _json_log_payloads(stream.getvalue())
    completed = _http_request_events(payloads, http_event="completed")[-1]
    assert completed.get("http_status") == 401
    assert str(completed.get("level") or "").lower() == "warning"


def test_error_json_includes_request_id_matching_propagation(logging_client) -> None:
    client, _stream = logging_client
    r = client.get(
        "/api/v1/bots",
        headers={"X-Request-ID": "err-req-99"},
    )
    assert r.status_code == 401
    body = r.json()
    err = body.get("error") or {}
    assert err.get("request_id") == "err-req-99"
    assert (r.headers.get("X-Request-ID") or r.headers.get("x-request-id")) == "err-req-99"


def test_sequential_requests_get_distinct_ids(logging_client) -> None:
    client, _stream = logging_client
    r1 = client.get("/api/v1/health")
    r2 = client.get("/api/v1/health")
    id1 = r1.headers.get("X-Request-ID") or r1.headers.get("x-request-id")
    id2 = r2.headers.get("X-Request-ID") or r2.headers.get("x-request-id")
    assert id1 != id2


def test_public_widget_path_infers_channel_in_http_log(logging_client) -> None:
    client, stream = logging_client
    r = client.get("/api/v1/public/widget/test-widget-key-123/bootstrap")
    # Bootstrap may return 4xx for bad key, 200 when DB+key exist, or 500 when DB is unreachable;
    # middleware must still tag the ingress channel from the path.
    assert r.status_code in (200, 400, 403, 404, 422, 500)
    payloads = _json_log_payloads(stream.getvalue())
    http_rows = _http_request_events(payloads, http_event="completed") + _http_request_events(
        payloads, http_event="failed"
    )
    assert http_rows, "expected http_request completed or failed log line"
    assert any(row.get("channel") == CONVERSATION_CHANNEL_WEB_WIDGET for row in http_rows)
