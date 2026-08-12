"""Deterministic intent rule engine."""

from __future__ import annotations

import pytest
from app.models.conversation_flow import ConversationDetectedIntent
from app.services.intent_rule_engine import classify_by_rules


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Hello!", ConversationDetectedIntent.greeting),
        ("hey there", ConversationDetectedIntent.greeting),
        ("Good morning", ConversationDetectedIntent.greeting),
        ("I need help with my order", ConversationDetectedIntent.support),
        ("The app is broken", ConversationDetectedIntent.support),
        ("What is your pricing?", ConversationDetectedIntent.sales_interest),
        ("Can I get a demo?", ConversationDetectedIntent.sales_interest),
        ("We need a strategy audit", ConversationDetectedIntent.consulting),
        ("What is your return policy", ConversationDetectedIntent.faq),
        ("How do I reset my password", ConversationDetectedIntent.faq),
    ],
)
def test_rule_engine_matches_expected_intent(message: str, expected: ConversationDetectedIntent) -> None:
    out = classify_by_rules(message)
    assert out is not None
    intent, conf = out
    assert intent == expected
    assert conf >= 0.7


def test_long_greeting_with_request_not_classified_as_greeting_only() -> None:
    """Avoid greeting label when the user also states a business need."""
    out = classify_by_rules("Hi, I need a refund for order 123")
    assert out is not None
    assert out[0] == ConversationDetectedIntent.support


def test_ambiguous_message_defers_to_ai() -> None:
    assert classify_by_rules("Hmm interesting") is None
    assert classify_by_rules("zqwxplkmnobody") is None


def test_is_rule_engine_opening_or_ack() -> None:
    from app.services.intent_rule_engine import is_rule_engine_opening_or_ack

    assert is_rule_engine_opening_or_ack("Hi") is True
    assert is_rule_engine_opening_or_ack("salom") is True
    assert is_rule_engine_opening_or_ack("ok") is True
    assert is_rule_engine_opening_or_ack("I need a refund") is False
