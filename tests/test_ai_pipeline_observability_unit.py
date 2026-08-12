"""Structured ai_pipeline_turn logging + token heuristics."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

from app.core.ai_pipeline_observability import (
    cache_type_for_step,
    estimate_tokens_saved_vs_llm,
    rough_token_estimate_chars_div4,
    track_ai_usage,
)
from app.schemas.ai_usage import (
    AI_USAGE_STEP_EXACT_CACHE,
    AI_USAGE_STEP_LLM_CALL,
    AI_USAGE_STEP_SEMANTIC_CACHE,
    AI_USAGE_STEP_TRIVIAL,
)


def test_rough_token_estimate_chars_div4() -> None:
    assert rough_token_estimate_chars_div4("abcd", chars_per_token=4.0) == 1
    assert rough_token_estimate_chars_div4("", chars_per_token=4.0) == 0


def test_cache_type_for_step() -> None:
    assert cache_type_for_step(AI_USAGE_STEP_EXACT_CACHE) == "exact"
    assert cache_type_for_step(AI_USAGE_STEP_SEMANTIC_CACHE) == "semantic"
    assert cache_type_for_step(AI_USAGE_STEP_LLM_CALL) == "none"
    assert cache_type_for_step(AI_USAGE_STEP_TRIVIAL) == "none"


def test_estimate_tokens_saved_positive() -> None:
    n = estimate_tokens_saved_vs_llm(
        user_text="hi",
        history_message_contents=["a" * 400],
        assistant_reply="reply",
        system_prompt_char_budget=400,
        chars_per_token=4.0,
    )
    assert n > 0


def test_track_ai_usage_emits_pipeline_event() -> None:
    log = MagicMock()
    bid = uuid.uuid4()
    cid = uuid.uuid4()
    track_ai_usage(
        log,
        bot_id=bid,
        conversation_id=cid,
        channel="admin_test",
        step_kind=AI_USAGE_STEP_TRIVIAL,
        provider_name="internal",
        model_name="trivial_filter",
        input_tokens=0,
        output_tokens=0,
        total_tokens=0,
        estimated_cost_usd=Decimal("0"),
        response_time_ms=3,
        cache_type="none",
        tokens_saved_est=120,
        success=True,
        used_token_estimation=False,
    )
    log.info.assert_called_once()
    args, kwargs = log.info.call_args
    assert args[0] == "ai_pipeline_turn"
    assert kwargs["step_kind"] == "trivial_handled"
    assert kwargs["input_tokens"] == 0
    assert kwargs["output_tokens"] == 0
    assert kwargs["total_tokens"] == 0
    assert kwargs["estimated_cost_usd"] == 0.0
    assert kwargs["response_time_ms"] == 3
    assert kwargs["cache_type"] == "none"
    assert kwargs["tokens_saved_est"] == 120
    assert kwargs["bot_id"] == str(bid)
