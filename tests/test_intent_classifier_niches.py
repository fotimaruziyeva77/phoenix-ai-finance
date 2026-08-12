"""
Niche-focused intent checks: Uzbek practical phrases + stable typing.

Rules must classify without live Gemini; service tests assert end-to-end shape.
"""

from __future__ import annotations

import asyncio

import pytest
from app.ai_providers.types import NormalizedAIResult
from app.core.config import Settings
from app.models.conversation_flow import ConversationDetectedIntent
from app.services.intent_classifier_service import IntentClassifierService
from app.services.intent_rule_engine import classify_by_rules
from app.services.intent_types import IntentClassificationResult


def test_education_uzbek_math_course_is_sales_interest() -> None:
    msg = "Farzandim uchun matematika kursi kerak"
    out = classify_by_rules(msg)
    assert out is not None
    assert out[0] == ConversationDetectedIntent.sales_interest
    assert out[1] >= 0.75


def test_healthcare_uzbek_dentist_booking_is_sales_interest() -> None:
    msg = "Stomatolog qabuliga yozilmoqchiman"
    out = classify_by_rules(msg)
    assert out is not None
    assert out[0] == ConversationDetectedIntent.sales_interest


def test_dev_uzbek_online_store_is_sales_interest() -> None:
    msg = "Menga online magazin kerak"
    out = classify_by_rules(msg)
    assert out is not None
    assert out[0] == ConversationDetectedIntent.sales_interest


def test_services_uzbek_home_craftsman_is_sales_interest() -> None:
    msg = "Uyimga usta kerak"
    out = classify_by_rules(msg)
    assert out is not None
    assert out[0] == ConversationDetectedIntent.sales_interest


def test_uzbek_greeting_classifies_as_greeting() -> None:
    out = classify_by_rules("Assalomu alaykum!")
    assert out is not None
    assert out[0] == ConversationDetectedIntent.greeting


def test_uzbek_smalltalk_defers_to_ai_or_unknown() -> None:
    """No clear commercial intent — rules return None (AI or unknown upstream)."""
    assert classify_by_rules("Bugun havo juda chiroyli ekan") is None


def test_english_support_and_faq_still_reasonable() -> None:
    sup = classify_by_rules("I was charged twice, please help")
    assert sup is not None and sup[0] == ConversationDetectedIntent.support
    faq = classify_by_rules("What are your office hours?")
    assert faq is not None and faq[0] == ConversationDetectedIntent.faq


def test_classifier_service_output_typed_and_stable_for_niche_phrase() -> None:
    async def run() -> None:
        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": None,
                }
            ),
            ai_provider=None,
        )
        msg = "Menga online magazin kerak"
        res = await svc.classify(msg)
        assert isinstance(res, IntentClassificationResult)
        assert res.intent == ConversationDetectedIntent.sales_interest
        assert res.source == "rules"
        assert isinstance(res.confidence, float)
        assert 0.0 <= res.confidence <= 1.0

    asyncio.run(run())


def test_unknown_message_without_ai_is_safe_unknown() -> None:
    async def run() -> None:
        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": None,
                }
            ),
            ai_provider=None,
        )
        res = await svc.classify("Bugun havo juda chiroyli ekan")
        assert res.intent == ConversationDetectedIntent.unknown
        assert res.source == "fallback"
        assert res.confidence < 0.5

    asyncio.run(run())


class _StubAI:
    def __init__(self, payload: NormalizedAIResult) -> None:
        self._payload = payload

    async def generate_response(self, params):
        return self._payload


def test_mocked_ai_classifies_when_rules_miss() -> None:
    """Deferred phrases still get stable typing via Gemini path (mocked)."""

    async def run() -> None:
        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": "stub",
                }
            ),
            ai_provider=_StubAI(
                NormalizedAIResult(
                    success=True,
                    provider_name="gemini",
                    text='{"intent":"faq","confidence":0.9}',
                    model_name="m",
                ),
            ),
        )
        res = await svc.classify("Bugun havo juda chiroyli ekan")
        assert isinstance(res, IntentClassificationResult)
        assert res.intent == ConversationDetectedIntent.faq
        assert res.source == "gemini"
        assert res.confidence == pytest.approx(0.9)

    asyncio.run(run())
