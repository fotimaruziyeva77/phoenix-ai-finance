"""Structured logging output."""

import json

import pytest
from app.core.logging import configure_logging, get_logger


@pytest.fixture(autouse=True)
def _reset_logging():
    yield
    import logging

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.WARNING)


def test_json_logs_emit_parseable_structured_lines(capsys):
    configure_logging(
        log_level="INFO",
        json_logs=True,
        service_name="test-service",
        environment="test",
        suppress_uvicorn_access=True,
    )

    get_logger("test").info("user_action", action="ping", ok=True)

    captured = capsys.readouterr().out
    lines = [ln for ln in captured.splitlines() if ln.strip()]
    assert lines, "expected at least one stdout log line"

    matching = [ln for ln in lines if "user_action" in ln]
    assert matching, f"no line contained user_action: {lines!r}"
    payload = json.loads(matching[-1])

    assert payload.get("event") == "user_action"
    assert payload.get("action") == "ping"
    assert payload.get("ok") is True
    assert "timestamp" in payload
    assert payload.get("service") == "test-service"
    assert payload.get("environment") == "test"
