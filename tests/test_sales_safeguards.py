"""Unit tests for :mod:`app.services.sales_safeguards` (no DB)."""

from __future__ import annotations

import pytest
from app.models.conversation_flow import ConversationDetectedIntent
from app.services.intent_types import IntentClassificationResult
from app.services.sales_safeguards import (
    SALES_RATE_MAX_TURNS_IN_WINDOW,
    SALES_USER_HARD_MAX_CHARS,
    SALES_WEAK_GEMINI_CONFIDENCE,
    SafeguardDecision,
    effective_routing_intent,
    evaluate_early_turn_guards,
    evaluate_post_extraction_guards,
)


def test_early_rate_limit_triggers_after_window_capacity() -> None:
    collected: dict[str, object] = {}
    base = 1_700_000_000.0
    last: SafeguardDecision | None = None
    for i in range(SALES_RATE_MAX_TURNS_IN_WINDOW + 1):
        last = evaluate_early_turn_guards(f"turn-{i}", collected, now=base)
    assert last is not None
    assert last.block_llm is True
    assert last.reason_code == "safeguard_rate_limit"
    assert "quickly" in (last.canned_user_message or "").lower()


def test_early_identical_short_message_spam() -> None:
    collected: dict[str, object] = {}
    base = 1_700_000_000.0
    last: SafeguardDecision | None = None
    for i in range(5):
        last = evaluate_early_turn_guards("ok", collected, now=base + i * 0.01)
    assert last is not None
    assert last.reason_code == "safeguard_identical_spam"


def test_early_message_too_long() -> None:
    collected: dict[str, object] = {}
    text = "a" * (SALES_USER_HARD_MAX_CHARS + 1)
    d = evaluate_early_turn_guards(text, collected, now=0.0)
    assert d is not None
    assert d.reason_code == "safeguard_message_too_long"
    assert "longer" in (d.canned_user_message or "").lower()


def test_effective_routing_intent_weak_gemini_becomes_unknown() -> None:
    ic = IntentClassificationResult(
        intent=ConversationDetectedIntent.sales_interest,
        confidence=SALES_WEAK_GEMINI_CONFIDENCE - 0.01,
        source="gemini",
    )
    assert effective_routing_intent(ic) is ConversationDetectedIntent.unknown


def test_effective_routing_intent_strong_gemini_unchanged() -> None:
    ic = IntentClassificationResult(
        intent=ConversationDetectedIntent.sales_interest,
        confidence=SALES_WEAK_GEMINI_CONFIDENCE,
        source="gemini",
    )
    assert effective_routing_intent(ic) is ConversationDetectedIntent.sales_interest


def test_effective_routing_intent_sales_default_passthrough() -> None:
    ic = IntentClassificationResult(
        intent=ConversationDetectedIntent.sales_interest,
        confidence=0.55,
        source="sales_default",
    )
    assert effective_routing_intent(ic) is ConversationDetectedIntent.sales_interest


def test_effective_routing_intent_rules_ignore_confidence_floor() -> None:
    ic = IntentClassificationResult(
        intent=ConversationDetectedIntent.sales_interest,
        confidence=0.1,
        source="rules",
    )
    assert effective_routing_intent(ic) is ConversationDetectedIntent.sales_interest


def test_post_extraction_success_resets_streaks() -> None:
    collected: dict[str, object] = {
        "_sf_miss_streak": 3,
        "_sf_vague_streak": 3,
        "_sf_miss_field": "email",
    }
    r = evaluate_post_extraction_guards(
        "user@example.com",
        extraction_target="email",
        keys_written=("email",),
        collected=collected,
    )
    assert r is None
    assert collected.get("_sf_miss_streak") == 0
    assert collected.get("_sf_vague_streak") == 0


@pytest.mark.parametrize(
    "text",
    ["?", "..", "a", "ok"],
)
def test_post_repeated_vague_triggers_safeguard(text: str) -> None:
    collected: dict[str, object] = {}
    last: SafeguardDecision | None = None
    for _ in range(4):
        last = evaluate_post_extraction_guards(
            text,
            extraction_target="student_grade",
            keys_written=(),
            collected=collected,
        )
    assert last is not None
    assert last.reason_code == "safeguard_vague_repeated"


def test_early_exactly_max_chars_does_not_trigger_length_block() -> None:
    collected: dict[str, object] = {}
    text = "a" * SALES_USER_HARD_MAX_CHARS
    assert evaluate_early_turn_guards(text, collected, now=0.0) is None


def test_post_without_target_does_not_touch_streak_flags() -> None:
    collected: dict[str, object] = {"_sf_vague_streak": 2, "_sf_miss_streak": 2}
    r = evaluate_post_extraction_guards(
        "?",
        extraction_target=None,
        keys_written=(),
        collected=collected,
    )
    assert r is None
    assert collected.get("_sf_vague_streak") == 2
    assert collected.get("_sf_miss_streak") == 2


def test_post_substantive_text_same_slot_miss_increments_until_cap() -> None:
    collected: dict[str, object] = {}
    for i in range(3):
        d = evaluate_post_extraction_guards(
            f"purple banana orbit {i}",
            extraction_target="email",
            keys_written=(),
            collected=collected,
        )
        assert d is None
    assert int(collected.get("_sf_miss_streak", 0)) == 3


def test_post_same_slot_miss_loop_resets_and_clarifies() -> None:
    collected: dict[str, object] = {}
    last: SafeguardDecision | None = None
    for _ in range(4):
        last = evaluate_post_extraction_guards(
            "blue elephant sky",
            extraction_target="budget",
            keys_written=(),
            collected=collected,
        )
    assert last is not None
    assert last.reason_code == "safeguard_same_slot_loop"
    assert int(collected.get("_sf_miss_streak", -1)) == 0
    assert "_sf_miss_field" not in collected
