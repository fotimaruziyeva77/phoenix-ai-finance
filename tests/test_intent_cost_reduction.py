"""
Intent classifier cost-reduction tests.

Coverage
--------
* Greetings (EN/UZ/RU) never call the intent model.
* Clear pricing / sales questions hit rules — model never called.
* Availability inquiries hit rules — model never called.
* Contact requests hit rules — model never called.
* Booking / speak-with-human requests hit rules — model never called.
* Uzbek-specific niche patterns hit rules — model never called.
* ``intent_model_skipped`` is logged when rules miss and AI is disabled.
* Only genuinely ambiguous, long text reaches the model.
* Default settings (``ai_sales_use_model_for_intent_when_rules_miss=False``) are cost-safe.
"""

from __future__ import annotations

import asyncio
import logging

import pytest

from app.ai_providers.types import NormalizedAIResult
from app.core.config import Settings
from app.models.conversation_flow import ConversationDetectedIntent
from app.services.intent_classifier_service import IntentClassifierService
from app.services.intent_rule_engine import classify_by_rules


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _settings(*, use_ai: bool = False, ambiguity_only: bool = True) -> Settings:
    return Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "test-key",
            "ai_sales_use_model_for_intent_when_rules_miss": use_ai,
            "ai_sales_intent_gemini_ambiguity_only": ambiguity_only,
        }
    )


class _SpyAI:
    """Provider that records calls; raises if unexpected invocation."""

    def __init__(self, *, should_be_called: bool = False) -> None:
        self.calls: int = 0
        self._should_be_called = should_be_called

    async def generate_response(self, params):
        self.calls += 1
        if not self._should_be_called:
            raise AssertionError(
                f"Gemini must NOT be called for this message. Called {self.calls} time(s)."
            )
        return NormalizedAIResult(
            success=True,
            provider_name="gemini",
            text='{"intent":"faq","confidence":0.9}',
            model_name="m",
        )


def _svc(*, use_ai: bool = False, ambiguity_only: bool = True, should_call_ai: bool = False):
    return IntentClassifierService(
        settings=_settings(use_ai=use_ai, ambiguity_only=ambiguity_only),
        ai_provider=_SpyAI(should_be_called=should_call_ai),
    )


# ---------------------------------------------------------------------------
# 1. Rule engine unit tests (synchronous, zero I/O)
# ---------------------------------------------------------------------------


class TestRuleEngineDirectCoverage:
    """Verify classify_by_rules() returns a hit without any async overhead."""

    # --- Greetings ---
    @pytest.mark.parametrize("text", ["hi", "hello", "Hey!", "good morning", "Howdy"])
    def test_english_greetings_hit_rules(self, text: str) -> None:
        result = classify_by_rules(text)
        assert result is not None
        intent, conf = result
        assert intent == ConversationDetectedIntent.greeting
        assert conf >= 0.9

    @pytest.mark.parametrize("text", ["salom", "Assalomu alaykum", "assalomu alaykum!"])
    def test_uzbek_greetings_hit_rules(self, text: str) -> None:
        result = classify_by_rules(text)
        assert result is not None
        intent, _ = result
        assert intent == ConversationDetectedIntent.greeting

    # --- Pricing / sales ---
    @pytest.mark.parametrize(
        "text",
        [
            "What is the pricing?",
            "How much does it cost?",
            "I want to buy the pro plan",
            "Give me a quote for 5 users",
            "Can I get a demo?",
            "Sign up for the trial",
        ],
    )
    def test_pricing_sales_messages_hit_rules(self, text: str) -> None:
        result = classify_by_rules(text)
        assert result is not None
        intent, conf = result
        assert intent == ConversationDetectedIntent.sales_interest
        assert conf >= 0.8

    # --- Availability ---
    @pytest.mark.parametrize(
        "text",
        [
            "Is that product available?",
            "Do you have this item in stock?",
            "Do you offer enterprise plans?",
            "Is the premium tier available?",
            "Do you sell annual subscriptions?",
        ],
    )
    def test_availability_messages_hit_rules(self, text: str) -> None:
        result = classify_by_rules(text)
        assert result is not None
        intent, conf = result
        assert intent == ConversationDetectedIntent.sales_interest
        assert conf >= 0.8

    # --- Contact ---
    # Note: "How do I contact support?" intentionally maps to SUPPORT (support markers fire first).
    # These examples are pure contact-channel inquiries with no support-problem signal.
    @pytest.mark.parametrize(
        "text",
        [
            "Can you give me your phone number?",
            "What is your email address?",
            "Please call me back",
            "Reach out to me on WhatsApp",
            "Get in touch with your team",
            "What is your WhatsApp number?",
        ],
    )
    def test_contact_messages_hit_rules(self, text: str) -> None:
        result = classify_by_rules(text)
        assert result is not None
        intent, conf = result
        assert intent == ConversationDetectedIntent.sales_interest
        assert conf >= 0.8

    # --- Booking / speak with human ---
    @pytest.mark.parametrize(
        "text",
        [
            "I want to book an appointment",
            "Can I schedule a meeting?",
            "I want to speak with a manager",
            "Connect me to a live agent",
            "Talk to a real person please",
            "I'd like to meet with your team",
        ],
    )
    def test_booking_messages_hit_rules(self, text: str) -> None:
        result = classify_by_rules(text)
        assert result is not None
        intent, conf = result
        assert intent == ConversationDetectedIntent.sales_interest
        assert conf >= 0.8

    # --- Short acknowledgements ---
    @pytest.mark.parametrize("text", ["ok", "thanks", "sure", "got it", "alright"])
    def test_short_ack_hit_rules(self, text: str) -> None:
        result = classify_by_rules(text)
        assert result is not None
        intent, _ = result
        assert intent == ConversationDetectedIntent.sales_interest

    # --- Support takes priority over contact when support signal present ---
    def test_contact_with_support_signal_maps_to_support(self) -> None:
        # "How do I contact support?" has the word "support" → support wins (correct priority)
        result = classify_by_rules("How do I contact support?")
        assert result is not None
        assert result[0] == ConversationDetectedIntent.support

    # --- Support ---
    @pytest.mark.parametrize("text", ["It's broken", "I have an issue", "please refund me"])
    def test_support_messages_hit_rules(self, text: str) -> None:
        result = classify_by_rules(text)
        assert result is not None
        intent, _ = result
        assert intent == ConversationDetectedIntent.support

    # --- Uzbek niche ---
    def test_uz_education_need_hits_rules(self) -> None:
        result = classify_by_rules("Farzandim uchun matematika kursi kerak")
        assert result is not None
        assert result[0] == ConversationDetectedIntent.sales_interest

    def test_uz_healthcare_booking_hits_rules(self) -> None:
        result = classify_by_rules("Stomatologga navbat olmoqchi edim")
        assert result is not None
        assert result[0] == ConversationDetectedIntent.sales_interest

    def test_uz_home_trades_hits_rules(self) -> None:
        result = classify_by_rules("Uyga usta kerak, santexnik bormi?")
        assert result is not None
        assert result[0] == ConversationDetectedIntent.sales_interest

    # --- Rules miss on genuinely ambiguous text ---
    def test_truly_ambiguous_returns_none(self) -> None:
        result = classify_by_rules("qzxvplmnop frobnicator glorp")
        assert result is None, "Gibberish must not match any rule"


# ---------------------------------------------------------------------------
# 2. Full classifier path — model never called for rule-covered messages
# ---------------------------------------------------------------------------


class TestModelNeverCalledForClearIntents:

    def test_greeting_no_model(self) -> None:
        svc = _svc(use_ai=True)
        spy = svc._ai_provider  # type: ignore[attr-defined]

        async def run() -> None:
            await svc.classify("Hello!", use_ai_when_rules_miss=True, sales_funnel_bot=True)

        asyncio.run(run())
        assert spy.calls == 0

    def test_pricing_question_no_model(self) -> None:
        svc = _svc(use_ai=True)
        spy = svc._ai_provider  # type: ignore[attr-defined]

        async def run() -> None:
            await svc.classify(
                "What is the pricing for teams?",
                use_ai_when_rules_miss=True,
                sales_funnel_bot=True,
            )

        asyncio.run(run())
        assert spy.calls == 0

    def test_availability_no_model(self) -> None:
        svc = _svc(use_ai=True)
        spy = svc._ai_provider  # type: ignore[attr-defined]

        async def run() -> None:
            await svc.classify(
                "Do you have enterprise plans available?",
                use_ai_when_rules_miss=True,
                sales_funnel_bot=True,
            )

        asyncio.run(run())
        assert spy.calls == 0

    def test_contact_no_model(self) -> None:
        svc = _svc(use_ai=True)
        spy = svc._ai_provider  # type: ignore[attr-defined]

        async def run() -> None:
            await svc.classify(
                "Can I get your WhatsApp number?",
                use_ai_when_rules_miss=True,
                sales_funnel_bot=True,
            )

        asyncio.run(run())
        assert spy.calls == 0

    def test_booking_no_model(self) -> None:
        svc = _svc(use_ai=True)
        spy = svc._ai_provider  # type: ignore[attr-defined]

        async def run() -> None:
            await svc.classify(
                "I need to book an appointment with your team.",
                use_ai_when_rules_miss=True,
                sales_funnel_bot=True,
            )

        asyncio.run(run())
        assert spy.calls == 0

    def test_uzbek_greeting_no_model(self) -> None:
        svc = _svc(use_ai=True)
        spy = svc._ai_provider  # type: ignore[attr-defined]

        async def run() -> None:
            await svc.classify(
                "Assalomu alaykum",
                use_ai_when_rules_miss=True,
                sales_funnel_bot=True,
            )

        asyncio.run(run())
        assert spy.calls == 0


# ---------------------------------------------------------------------------
# 3. Default settings are cost-safe (model disabled)
# ---------------------------------------------------------------------------


class TestDefaultSettingsAreCostSafe:
    """With factory defaults, Gemini is NEVER called for intent classification."""

    @pytest.mark.parametrize(
        "message",
        [
            "hi",
            "what is the price?",
            "do you offer a free trial?",
            "is that available?",
            "can I book a meeting?",
            "call me back please",
            "mystery gibberish text xyz",  # rules miss → sales_default, NOT model
        ],
    )
    def test_no_model_call_with_default_settings(self, message: str) -> None:
        svc = _svc(use_ai=False)
        spy = svc._ai_provider  # type: ignore[attr-defined]

        async def run() -> None:
            await svc.classify(message, use_ai_when_rules_miss=False, sales_funnel_bot=True)

        asyncio.run(run())
        assert spy.calls == 0

    def test_rules_miss_with_ai_disabled_returns_sales_default(self) -> None:
        svc = _svc(use_ai=False)

        async def run():
            return await svc.classify(
                "qzxvplmnop unique_gibberish_xyz",
                use_ai_when_rules_miss=False,
                sales_funnel_bot=True,
            )

        out = asyncio.run(run())
        assert out.source == "sales_default"
        assert out.intent == ConversationDetectedIntent.sales_interest

    def test_rules_miss_with_ai_disabled_non_sales_returns_fallback(self) -> None:
        svc = _svc(use_ai=False)

        async def run():
            return await svc.classify(
                "qzxvplmnop unique_gibberish_xyz",
                use_ai_when_rules_miss=False,
                sales_funnel_bot=False,
            )

        out = asyncio.run(run())
        assert out.source == "fallback"
        assert out.intent == ConversationDetectedIntent.unknown


# ---------------------------------------------------------------------------
# 4. intent_model_skipped log is emitted on both bypass paths
# ---------------------------------------------------------------------------


class TestIntentModelSkippedLog:

    def test_log_emitted_when_use_ai_disabled(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        svc = _svc(use_ai=False)

        async def run() -> None:
            await svc.classify(
                "something with no rule match zeta-unique",
                use_ai_when_rules_miss=False,
                sales_funnel_bot=True,
            )

        with caplog.at_level(logging.DEBUG, logger="app.services.intent_classifier_service"):
            asyncio.run(run())

        assert any("intent_model_skipped" in r.message for r in caplog.records)

    def test_log_emitted_when_ambiguity_gate_blocks_model(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Short text + ambiguity_only=True → model skipped log fires."""
        svc = _svc(use_ai=True, ambiguity_only=True)

        async def run() -> None:
            await svc.classify(
                "qzxvplmnop",  # rules miss, short = not ambiguous
                use_ai_when_rules_miss=True,
                sales_funnel_bot=True,
            )

        with caplog.at_level(logging.DEBUG, logger="app.services.intent_classifier_service"):
            asyncio.run(run())

        assert any("intent_model_skipped" in r.message for r in caplog.records)

    def test_no_skipped_log_when_model_is_actually_called(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When the model IS called, intent_model_used fires — intent_model_skipped must NOT."""
        svc = IntentClassifierService(
            settings=_settings(use_ai=True, ambiguity_only=False),
            ai_provider=_SpyAI(should_be_called=True),
        )
        text = "maybe we " + "need something unclear " * 12

        async def run() -> None:
            await svc.classify(text, use_ai_when_rules_miss=True, sales_funnel_bot=True)

        with caplog.at_level(logging.DEBUG, logger="app.services.intent_classifier_service"):
            asyncio.run(run())

        assert any("intent_model_used" in r.message for r in caplog.records)
        assert not any("intent_model_skipped" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# 5. Only genuinely ambiguous long text reaches Gemini
# ---------------------------------------------------------------------------


class TestOnlyAmbiguousTextCallsGemini:

    def test_long_ambiguous_text_calls_model_once(self) -> None:
        svc = IntentClassifierService(
            settings=_settings(use_ai=True, ambiguity_only=True),
            ai_provider=_SpyAI(should_be_called=True),
        )
        spy = svc._ai_provider  # type: ignore[attr-defined]
        text = "maybe we " + "need something unclear " * 12

        async def run() -> None:
            await svc.classify(text, use_ai_when_rules_miss=True, sales_funnel_bot=True)

        asyncio.run(run())
        assert spy.calls == 1

    def test_short_clear_text_does_not_call_model(self) -> None:
        svc = _svc(use_ai=True, ambiguity_only=True)
        spy = svc._ai_provider  # type: ignore[attr-defined]

        async def run() -> None:
            await svc.classify("buy", use_ai_when_rules_miss=True, sales_funnel_bot=True)

        asyncio.run(run())
        # "buy" matches _SALES_MARKERS → rules hit → model never reached
        assert spy.calls == 0

    def test_ambiguity_only_false_allows_model_for_any_miss(self) -> None:
        """With ambiguity_only=False, even short ambiguous text may call the model."""
        svc = IntentClassifierService(
            settings=_settings(use_ai=True, ambiguity_only=False),
            ai_provider=_SpyAI(should_be_called=True),
        )
        spy = svc._ai_provider  # type: ignore[attr-defined]

        async def run() -> None:
            await svc.classify(
                "qzxvplmnop unique_gibberish",
                use_ai_when_rules_miss=True,
                sales_funnel_bot=True,
            )

        asyncio.run(run())
        assert spy.calls == 1
