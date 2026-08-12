"""Sales LLM protection: rate-limit soft reply, burst skip, intent ambiguity gate."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis as fakeredis
import pytest
from app.ai_providers.base import AIProvider
from app.ai_providers.types import GenerateParams, NormalizedAIResult, TokenUsage
from app.core.config import Settings
from app.integrations.providers.gemini_errors import RATE_LIMITED
from app.models.ai_foundation import Conversation
from app.models.bot import Bot
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.bot_repository import BotRepository
from app.services.intent_types import IntentClassificationResult
from app.services.sales_conversation_orchestrator import SalesConversationOrchestrator
from app.services.sales_llm_burst_limiter import SalesLLMBurstLimiter


class TrackingStubProvider(AIProvider):
    def __init__(self, reply_text: str = "Thanks — noted.") -> None:
        self._reply = reply_text
        self.generate_response_calls = 0

    @property
    def provider_name(self) -> str:
        return "stub"

    @property
    def default_model(self) -> str:
        return "stub-model"

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        self.generate_response_calls += 1
        return NormalizedAIResult(
            success=True,
            provider_name=self.provider_name,
            text=self._reply,
            model_name=params.model,
            tokens=TokenUsage(input_tokens=4, output_tokens=6, total_tokens=10),
        )

    def parse_usage(self, raw):
        return None

    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        return ("stub_error", str(exc))

    async def aclose(self) -> None:
        return None


class _RateLimitedChatProvider(TrackingStubProvider):
    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        self.generate_response_calls += 1
        return NormalizedAIResult(
            success=False,
            provider_name=self.provider_name,
            text=None,
            model_name=params.model,
            tokens=None,
            raw_usage=None,
            error_code=RATE_LIMITED,
            error_message="quota",
        )


def _intent_mock(intent: ConversationDetectedIntent) -> MagicMock:
    m = MagicMock()
    m.classify = AsyncMock(
        return_value=IntentClassificationResult(intent=intent, confidence=0.95, source="rules")
    )
    return m


def _make_bot(*, niche_id: str) -> Bot:
    oid = uuid.uuid4()
    return Bot(
        id=uuid.uuid4(),
        owner_id=oid,
        name="Test bot",
        niche_id=niche_id,
        goal_type="sales",
        status="active",
        provider_name="stub",
        model_name="stub-model",
    )


def _make_conv(bot: Bot, *, state: str) -> Conversation:
    return Conversation(
        id=uuid.uuid4(),
        bot_id=bot.id,
        owner_id=bot.owner_id,
        current_state=state,
        collected_data_json={},
    )


def _mock_repos(bot: Bot) -> tuple[MagicMock, MagicMock]:
    chat = MagicMock(spec=AIChatRepository)
    chat.list_recent_history_messages = AsyncMock(return_value=[])
    chat.add_message = AsyncMock(side_effect=lambda **kwargs: SimpleNamespace(id=uuid.uuid4()))
    chat.update_conversation_sales_flow = AsyncMock()
    chat.touch_conversation_updated_at = AsyncMock()
    chat.commit = AsyncMock()
    chat.rollback = AsyncMock()
    chat.add_usage_log = AsyncMock(side_effect=lambda **kwargs: SimpleNamespace(id=uuid.uuid4()))
    bots = MagicMock(spec=BotRepository)
    bots.get_bot_by_id = AsyncMock(return_value=bot)
    return chat, bots


def _stub_lead_repo() -> MagicMock:
    lr = MagicMock()
    lr.get_lead_by_conversation_id = AsyncMock(return_value=None)
    lr.find_open_lead_same_normalized_phone = AsyncMock(return_value=None)
    lr.count_leads_same_phone_recent = AsyncMock(return_value=0)
    lr.create_lead = AsyncMock(
        side_effect=lambda **kwargs: SimpleNamespace(
            id=uuid.uuid4(),
            created_at=None,
            **kwargs,
        )
    )
    return lr


@pytest.mark.asyncio
async def test_sales_chat_rate_limited_returns_soft_uz_success() -> None:
    bot = _make_bot(niche_id="generic")
    conv = _make_conv(bot, state=ConversationFlowState.start.value)
    chat, bots = _mock_repos(bot)
    stub = _RateLimitedChatProvider("unused")
    settings = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "dummy",
            "ai_trivial_greeting_fast_path_enabled": False,
            "ai_sales_llm_burst_protection_enabled": False,
            "ai_telegram_gemini_rate_limit_user_message_uz": "Hozir yuklama biroz yuqori.",
        }
    )

    def _res(_s: Settings, _pid: str | None) -> AIProvider:
        return stub

    orch = SalesConversationOrchestrator(
        chat,
        bots,
        settings=settings,
        intent_classifier=_intent_mock(ConversationDetectedIntent.sales_interest),
        provider_resolver=_res,
        lead_repo=_stub_lead_repo(),
        lead_owner_delivery=None,
        burst_limiter=SalesLLMBurstLimiter(settings, None),
    )
    r = await orch.process_sales_turn(bot, conv, "I need a quote for tutoring", persist_user_message=False)
    assert r.success is True
    assert r.assistant_text
    assert "yuklama" in (r.assistant_text or "").lower()
    assert stub.generate_response_calls == 1


@pytest.mark.asyncio
async def test_burst_skip_opening_when_window_saturated() -> None:
    bot = _make_bot(niche_id="generic")
    conv = _make_conv(bot, state=ConversationFlowState.start.value)
    chat, bots = _mock_repos(bot)
    stub = TrackingStubProvider("LLM body")
    settings = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "dummy",
            "ai_trivial_greeting_fast_path_enabled": False,
            "ai_sales_llm_burst_protection_enabled": True,
            "ai_sales_llm_burst_window_seconds": 30,
            "ai_sales_llm_burst_max_calls_per_window": 2,
        }
    )
    client = fakeredis.FakeRedis(decode_responses=True)
    limiter = SalesLLMBurstLimiter(settings, client)
    await limiter.record_llm_invocation(bot.id)
    await limiter.record_llm_invocation(bot.id)

    def _res(_s: Settings, _pid: str | None) -> AIProvider:
        return stub

    orch = SalesConversationOrchestrator(
        chat,
        bots,
        settings=settings,
        intent_classifier=_intent_mock(ConversationDetectedIntent.sales_interest),
        provider_resolver=_res,
        lead_repo=_stub_lead_repo(),
        lead_owner_delivery=None,
        burst_limiter=limiter,
    )
    r = await orch.process_sales_turn(bot, conv, "Hi", persist_user_message=False)
    assert r.success is True
    assert stub.generate_response_calls == 0
    assert r.assistant_text
