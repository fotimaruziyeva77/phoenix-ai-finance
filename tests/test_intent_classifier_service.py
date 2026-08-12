"""IntentClassifierService orchestration (mocked Gemini)."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest

from app.ai_providers.types import NormalizedAIResult
from app.core.config import Settings
from app.models.conversation_flow import ConversationDetectedIntent
from app.repositories.ai_chat_repository import AIChatRepository
from app.services.ai_usage_log_service import AIUsageLogService
from app.services.intent_classifier_service import IntentClassifierService
from app.services.intent_types import (
    IntentClassificationResult,
    IntentClassifierUsageContext,
    coerce_intent_label,
)


def test_coerce_intent_label_normalizes() -> None:
    assert coerce_intent_label("SALES_INTEREST") == ConversationDetectedIntent.sales_interest
    assert coerce_intent_label("sales-interest") == ConversationDetectedIntent.sales_interest
    assert coerce_intent_label("nope") is None


def test_intent_classification_result_confidence_bounds() -> None:
    IntentClassificationResult(
        intent=ConversationDetectedIntent.unknown,
        confidence=0.5,
        source="fallback",
    )
    with pytest.raises(ValueError):
        IntentClassificationResult(
            intent=ConversationDetectedIntent.unknown,
            confidence=1.5,
            source="fallback",
        )


class _StubAI:
    def __init__(self, payload: NormalizedAIResult) -> None:
        self._payload = payload

    async def generate_response(self, params):
        return self._payload


def test_rules_short_circuit_before_ai() -> None:
    async def run() -> None:
        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": "should-not-be-called",
                }
            ),
            ai_provider=_StubAI(
                NormalizedAIResult(
                    success=True,
                    provider_name="gemini",
                    text='{"intent":"support","confidence":0.99}',
                    model_name="m",
                ),
            ),
        )
        out = await svc.classify("Hello!")
        assert out.source == "rules"
        assert out.intent == ConversationDetectedIntent.greeting

    asyncio.run(run())


def test_gemini_json_parsed_when_rules_miss() -> None:
    async def run() -> None:
        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": "x",
                }
            ),
            ai_provider=_StubAI(
                NormalizedAIResult(
                    success=True,
                    provider_name="gemini",
                    text='{"intent":"consulting","confidence":0.91}',
                    model_name="m",
                ),
            ),
        )
        out = await svc.classify("We should explore synergies next quarter.")
        assert out.source == "gemini"
        assert out.intent == ConversationDetectedIntent.consulting
        assert out.confidence == pytest.approx(0.91)

    asyncio.run(run())


def test_low_confidence_from_model_maps_to_unknown() -> None:
    async def run() -> None:
        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": "x",
                }
            ),
            ai_provider=_StubAI(
                NormalizedAIResult(
                    success=True,
                    provider_name="gemini",
                    text='{"intent":"sales_interest","confidence":0.2}',
                    model_name="m",
                ),
            ),
        )
        out = await svc.classify("asdfgh random")
        assert out.intent == ConversationDetectedIntent.unknown
        assert out.source == "gemini"
        assert out.confidence == pytest.approx(0.2)

    asyncio.run(run())


def test_invalid_json_from_model_fallback() -> None:
    async def run() -> None:
        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": "x",
                }
            ),
            ai_provider=_StubAI(
                NormalizedAIResult(
                    success=True,
                    provider_name="gemini",
                    text="not json at all",
                    model_name="m",
                ),
            ),
        )
        out = await svc.classify("mystery phrase")
        assert out.intent == ConversationDetectedIntent.unknown
        assert out.source == "fallback"

    asyncio.run(run())


def test_ai_disabled_after_rules_miss_non_sales_maps_unknown() -> None:
    async def run() -> None:
        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": "x",
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
        out = await svc.classify(
            "mystery phrase",
            use_ai_when_rules_miss=False,
            sales_funnel_bot=False,
        )
        assert out.source == "fallback"
        assert out.intent == ConversationDetectedIntent.unknown

    asyncio.run(run())


def test_sales_funnel_default_skips_model_when_rules_miss() -> None:
    async def run() -> None:
        called = {"n": 0}

        class _NeverCallAI(_StubAI):
            async def generate_response(self, params):
                called["n"] += 1
                return await super().generate_response(params)

        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": "x",
                }
            ),
            ai_provider=_NeverCallAI(
                NormalizedAIResult(
                    success=True,
                    provider_name="gemini",
                    text='{"intent":"faq","confidence":0.9}',
                    model_name="m",
                ),
            ),
        )
        out = await svc.classify(
            "mystery phrase xyzzy unique",
            use_ai_when_rules_miss=False,
            sales_funnel_bot=True,
        )
        assert called["n"] == 0
        assert out.source == "sales_default"
        assert out.intent == ConversationDetectedIntent.sales_interest

    asyncio.run(run())


def test_rules_short_ack_avoids_model() -> None:
    async def run() -> None:
        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": "should-not-be-called",
                }
            ),
            ai_provider=_StubAI(
                NormalizedAIResult(
                    success=True,
                    provider_name="gemini",
                    text='{"intent":"support","confidence":0.99}',
                    model_name="m",
                ),
            ),
        )
        out = await svc.classify("thanks!")
        assert out.source == "rules"
        assert out.intent == ConversationDetectedIntent.sales_interest

    asyncio.run(run())


def test_gemini_intent_writes_usage_log_when_context_provided() -> None:
    async def run() -> None:
        chat = AsyncMock(spec=AIChatRepository)
        chat.add_usage_log = AsyncMock(return_value=AsyncMock())
        uls = AIUsageLogService(chat)
        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": "x",
                }
            ),
            ai_provider=_StubAI(
                NormalizedAIResult(
                    success=True,
                    provider_name="gemini",
                    text='{"intent":"faq","confidence":0.88}',
                    model_name="m",
                    tokens=None,
                ),
            ),
            usage_log_service=uls,
        )
        bid = uuid.uuid4()
        cid = uuid.uuid4()
        ctx = IntentClassifierUsageContext(bot_id=bid, conversation_id=cid)
        out = await svc.classify(
            "mystery phrase zeta-usage-log-intent-unique",
            usage_context=ctx,
        )
        assert out.source == "gemini"
        chat.add_usage_log.assert_awaited_once()
        kw = chat.add_usage_log.await_args.kwargs
        assert kw["step_kind"] == "intent_classifier"
        assert kw["bot_id"] == bid
        assert kw["conversation_id"] == cid

    asyncio.run(run())


def test_no_api_key_skips_model() -> None:
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
        out = await svc.classify("mystery phrase")
        assert out.source == "fallback"
        assert out.intent == ConversationDetectedIntent.unknown

    asyncio.run(run())


def test_markdown_fenced_json_still_parses() -> None:
    async def run() -> None:
        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": "x",
                }
            ),
            ai_provider=_StubAI(
                NormalizedAIResult(
                    success=True,
                    provider_name="gemini",
                    text='```json\n{"intent":"faq","confidence":0.88}\n```',
                    model_name="m",
                ),
            ),
        )
        out = await svc.classify("the square root of ambiguity plz")
        assert out.intent == ConversationDetectedIntent.faq
        assert out.source == "gemini"

    asyncio.run(run())


def test_sales_pricing_rules_hit_no_gemini_when_model_enabled() -> None:
    """Clear pricing question matches rules — never invoke Gemini even if rules-miss AI is on."""

    async def run() -> None:
        calls = {"n": 0}

        class _Spy:
            async def generate_response(self, params):
                calls["n"] += 1
                raise AssertionError("Gemini must not run for rule-covered pricing text")

        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": "x",
                    "ai_sales_use_model_for_intent_when_rules_miss": True,
                    "ai_sales_intent_gemini_ambiguity_only": True,
                }
            ),
            ai_provider=_Spy(),
        )
        out = await svc.classify(
            "What is the pricing for teams?",
            use_ai_when_rules_miss=True,
            sales_funnel_bot=True,
        )
        assert calls["n"] == 0
        assert out.source == "rules"
        assert out.intent == ConversationDetectedIntent.sales_interest

    asyncio.run(run())


def test_sales_ambiguity_gate_skips_gemini_for_short_non_ambiguous() -> None:
    async def run() -> None:
        calls = {"n": 0}

        class _Spy:
            async def generate_response(self, params):
                calls["n"] += 1
                return NormalizedAIResult(
                    success=True,
                    provider_name="gemini",
                    text='{"intent":"faq","confidence":0.9}',
                    model_name="m",
                )

        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": "x",
                    "ai_sales_use_model_for_intent_when_rules_miss": True,
                    "ai_sales_intent_gemini_ambiguity_only": True,
                }
            ),
            ai_provider=_Spy(),
        )
        out = await svc.classify(
            "qzxvplmnop",
            use_ai_when_rules_miss=True,
            sales_funnel_bot=True,
        )
        assert calls["n"] == 0
        assert out.source == "sales_default"
        assert out.intent == ConversationDetectedIntent.sales_interest

    asyncio.run(run())


def test_sales_ambiguity_allows_gemini_for_long_unclear_text() -> None:
    async def run() -> None:
        calls = {"n": 0}

        class _Spy:
            async def generate_response(self, params):
                calls["n"] += 1
                return NormalizedAIResult(
                    success=True,
                    provider_name="gemini",
                    text='{"intent":"faq","confidence":0.9}',
                    model_name="m",
                )

        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": "x",
                    "ai_sales_use_model_for_intent_when_rules_miss": True,
                    "ai_sales_intent_gemini_ambiguity_only": True,
                }
            ),
            ai_provider=_Spy(),
        )
        text = "maybe we " + "need something unclear " * 12
        out = await svc.classify(
            text,
            use_ai_when_rules_miss=True,
            sales_funnel_bot=True,
        )
        assert calls["n"] == 1
        assert out.source == "gemini"

    asyncio.run(run())


def test_intent_burst_record_callback_runs_after_gemini_call() -> None:
    async def run() -> None:
        bursts: list[int] = []

        async def _rec() -> None:
            bursts.append(1)

        svc = IntentClassifierService(
            settings=Settings.model_validate(
                {
                    "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
                    "gemini_api_key": "x",
                    "ai_sales_use_model_for_intent_when_rules_miss": True,
                    "ai_sales_intent_gemini_ambiguity_only": True,
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
        text = "maybe we " + "need something unclear " * 12
        cid = uuid.uuid4()
        bid = uuid.uuid4()
        await svc.classify(
            text,
            use_ai_when_rules_miss=True,
            sales_funnel_bot=True,
            usage_context=IntentClassifierUsageContext(
                bot_id=bid,
                conversation_id=cid,
                record_sales_llm_burst=_rec,
            ),
        )
        assert bursts == [1]

    asyncio.run(run())
