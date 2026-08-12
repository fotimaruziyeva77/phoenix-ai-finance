"""Unit tests for :mod:`app.core.ai_provider_observability` (no HTTP)."""

from __future__ import annotations

import json
import logging
import uuid

import pytest
from app.core.ai_provider_observability import log_ai_provider_call
from app.core.logging import configure_logging, get_logger


@pytest.fixture(autouse=True)
def _reset_logging() -> None:
    yield
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.WARNING)


def test_ai_provider_call_json_has_safe_metadata_only(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(
        log_level="INFO",
        json_logs=True,
        service_name="obs-test",
        environment="test",
        suppress_uvicorn_access=True,
    )
    log = get_logger("ai_obs_test")
    cid = uuid.uuid4()
    bid = uuid.uuid4()
    log_ai_provider_call(
        log,
        provider_name="test_provider",
        model_name="test-model",
        success=False,
        latency_ms=12,
        tokens_total=99,
        conversation_id=cid,
        bot_id=bid,
        channel="web_widget",
        call_kind="external",
        provider_error_code="rate_limited",
        ai_category="upstream",
    )
    out = capsys.readouterr().out
    line = next(ln for ln in out.splitlines() if "ai_provider_call" in ln)
    payload = json.loads(line.strip())
    assert payload.get("event") == "ai_provider_call"
    assert payload.get("ai_provider") == "test_provider"
    assert payload.get("ai_model") == "test-model"
    assert payload.get("ai_success") is False
    assert payload.get("ai_latency_ms") == 12
    assert payload.get("ai_tokens_total") == 99
    assert payload.get("conversation_id") == str(cid)
    assert payload.get("bot_id") == str(bid)
    assert payload.get("channel") == "web_widget"
    assert payload.get("ai_call_kind") == "external"
    assert payload.get("provider_error_code") == "rate_limited"
    assert payload.get("ai_category") == "upstream"
    blob = json.dumps(payload).lower()
    assert "prompt" not in blob
    assert "completion" not in blob
