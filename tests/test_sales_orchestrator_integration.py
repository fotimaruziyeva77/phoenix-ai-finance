"""
Integration-style tests for :class:`~app.services.sales_conversation_orchestrator.SalesConversationOrchestrator`.

Repositories are mocked; the AI completion provider is a stub. Intent classification is stubbed so
tests do not depend on rule coverage or live APIs.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.ai_providers.base import AIProvider
from app.ai_providers.types import GenerateParams, NormalizedAIResult, TokenUsage
from app.core.config import Settings, get_settings
from app.models.ai_foundation import Conversation
from app.models.bot import Bot
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.bot_repository import BotRepository
from app.repositories.lead_repository import LeadRepository
from app.services.intent_types import IntentClassificationResult
from app.services.response_planner import ResponseMode
from app.services.sales_conversation_orchestrator import ORCH_TARGET_FIELD_KEY, SalesConversationOrchestrator
from app.services.sales_safeguards import SALES_USER_HARD_MAX_CHARS


class StubAIProvider(AIProvider):
    """Deterministic provider for orchestrator tests."""

    def __init__(self, reply_text: str = "Thanks — noted.") -> None:
        self._reply = reply_text

    @property
    def provider_name(self) -> str:
        return "stub"

    @property
    def default_model(self) -> str:
        return "stub-model"

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        return NormalizedAIResult(
            success=True,
            provider_name=self.provider_name,
            text=self._reply,
            model_name=params.model,
            tokens=TokenUsage(input_tokens=4, output_tokens=6, total_tokens=10),
        )

    def parse_usage(self, raw: dict[str, Any] | None) -> TokenUsage | None:
        return None

    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        return ("stub_error", str(exc))

    async def aclose(self) -> None:
        return None


class TrackingStubProvider(StubAIProvider):
    """Stub that counts :meth:`generate_response` calls (safeguard paths must not call the LLM)."""

    def __init__(self, reply_text: str = "Thanks — noted.") -> None:
        super().__init__(reply_text)
        self.generate_response_calls = 0

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        self.generate_response_calls += 1
        return await super().generate_response(params)


def _intent_classifier_mock(intent: ConversationDetectedIntent) -> MagicMock:
    m = MagicMock()
    m.classify = AsyncMock(
        return_value=IntentClassificationResult(intent=intent, confidence=0.95, source="rules")
    )
    return m


def _stub_resolver(reply: str) -> Callable[[Settings, str | None], AIProvider]:
    def _resolve(_settings: Settings, _provider_id: str | None) -> AIProvider:
        return StubAIProvider(reply)

    return _resolve


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


def _make_conversation(bot: Bot, *, state: str, collected: dict[str, object] | None = None) -> Conversation:
    return Conversation(
        id=uuid.uuid4(),
        bot_id=bot.id,
        owner_id=bot.owner_id,
        current_state=state,
        collected_data_json=dict(collected or {}),
    )


def _stub_lead_repo() -> MagicMock:
    lr = MagicMock(spec=LeadRepository)
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


def _mock_repos(bot: Bot) -> tuple[MagicMock, MagicMock]:
    chat = MagicMock(spec=AIChatRepository)
    chat.list_recent_history_messages = AsyncMock(return_value=[])
    chat.add_message = AsyncMock(
        side_effect=lambda **kwargs: SimpleNamespace(id=uuid.uuid4()),
    )
    chat.update_conversation_sales_flow = AsyncMock()
    chat.touch_conversation_updated_at = AsyncMock()
    chat.commit = AsyncMock()
    chat.rollback = AsyncMock()
    chat.add_usage_log = AsyncMock(
        side_effect=lambda **kwargs: SimpleNamespace(id=uuid.uuid4()),
    )

    bots = MagicMock(spec=BotRepository)
    bots.get_bot_by_id = AsyncMock(return_value=bot)
    return chat, bots


def _orch(
    chat: MagicMock,
    bots: MagicMock,
    *,
    intent: ConversationDetectedIntent = ConversationDetectedIntent.sales_interest,
    reply: str = "Ack.",
    provider: AIProvider | None = None,
) -> SalesConversationOrchestrator:
    if provider is not None:

        def _resolve(_settings: Settings, _provider_id: str | None) -> AIProvider:
            return provider

        resolver: Callable[[Settings, str | None], AIProvider] = _resolve
    else:
        resolver = _stub_resolver(reply)
    # Match ``tests.test_ai_service._settings``: these tests assert on classifier + LLM behavior.
    base = get_settings()
    upd: dict = {}
    if base.ai_trivial_greeting_fast_path_enabled:
        upd["ai_trivial_greeting_fast_path_enabled"] = False
    if base.ai_sales_llm_burst_protection_enabled:
        upd["ai_sales_llm_burst_protection_enabled"] = False
    settings = base.model_copy(update=upd) if upd else base
    return SalesConversationOrchestrator(
        chat,
        bots,
        settings=settings,
        intent_classifier=_intent_classifier_mock(intent),
        provider_resolver=resolver,
        lead_repo=_stub_lead_repo(),
        lead_owner_delivery=None,
    )


@pytest.mark.asyncio
async def test_user_input_updates_collected_data_when_target_set() -> None:
    bot = _make_bot(niche_id="education")
    conv = _make_conversation(
        bot,
        state=ConversationFlowState.qualification.value,
        collected={ORCH_TARGET_FIELD_KEY: "student_grade"},
    )
    chat, bots = _mock_repos(bot)
    orch = _orch(chat, bots)

    result = await orch.process_sales_turn(
        bot,
        conv,
        "She is in 9th grade",
        persist_user_message=False,
    )

    assert "student_grade" in result.updated_collected_data
    assert result.updated_collected_data["student_grade"] == "Grade 9"
    assert "student_grade" in result.metadata.extraction_keys_written


@pytest.mark.asyncio
async def test_state_transition_start_to_qualification_with_sales_intent() -> None:
    bot = _make_bot(niche_id="education")
    conv = _make_conversation(bot, state=ConversationFlowState.start.value)
    chat, bots = _mock_repos(bot)
    orch = _orch(chat, bots, intent=ConversationDetectedIntent.sales_interest)

    result = await orch.process_sales_turn(
        bot,
        conv,
        "I want a quote for tutoring",
        persist_user_message=False,
    )

    assert result.metadata.previous_state == ConversationFlowState.start.value
    assert result.metadata.next_state == ConversationFlowState.qualification.value
    assert result.updated_current_state == ConversationFlowState.qualification.value


@pytest.mark.asyncio
async def test_next_question_target_field_first_missing_core() -> None:
    bot = _make_bot(niche_id="education")
    conv = _make_conversation(bot, state=ConversationFlowState.start.value)
    chat, bots = _mock_repos(bot)
    orch = _orch(chat, bots, intent=ConversationDetectedIntent.sales_interest)

    result = await orch.process_sales_turn(
        bot,
        conv,
        "pricing for math lessons please",
        persist_user_message=False,
    )

    assert result.updated_collected_data.get(ORCH_TARGET_FIELD_KEY) == "student_grade"
    assert result.metadata.question_planner_action == "ask_core_field"


@pytest.mark.asyncio
async def test_response_mode_acknowledge_for_sales_interest_with_question() -> None:
    bot = _make_bot(niche_id="education")
    conv = _make_conversation(bot, state=ConversationFlowState.qualification.value)
    chat, bots = _mock_repos(bot)
    orch = _orch(chat, bots, intent=ConversationDetectedIntent.sales_interest)

    result = await orch.process_sales_turn(
        bot,
        conv,
        "still deciding on format",
        persist_user_message=False,
    )

    assert result.metadata.response_mode == ResponseMode.acknowledge_and_ask.value


@pytest.mark.asyncio
async def test_response_mode_greeting_entry() -> None:
    bot = _make_bot(niche_id="education")
    conv = _make_conversation(bot, state=ConversationFlowState.start.value)
    chat, bots = _mock_repos(bot)
    orch = _orch(chat, bots, intent=ConversationDetectedIntent.greeting)

    result = await orch.process_sales_turn(
        bot,
        conv,
        "Hello",
        persist_user_message=False,
    )

    # After transition we are in qualification; greeting intent + scripted question → ask_question path
    assert result.metadata.response_mode == ResponseMode.ask_question.value


@pytest.mark.asyncio
async def test_conversation_state_persisted_via_repository() -> None:
    bot = _make_bot(niche_id="healthcare")
    conv = _make_conversation(bot, state=ConversationFlowState.start.value)
    chat, bots = _mock_repos(bot)
    orch = _orch(chat, bots, intent=ConversationDetectedIntent.sales_interest)

    await orch.process_sales_turn(
        bot,
        conv,
        "I need to book an appointment",
        persist_user_message=False,
    )

    chat.update_conversation_sales_flow.assert_awaited()
    call = chat.update_conversation_sales_flow.await_args
    assert call.args[0] == conv.id
    assert call.kwargs["current_state"] == ConversationFlowState.qualification.value
    assert call.kwargs["detected_intent"] == ConversationDetectedIntent.sales_interest.value
    assert isinstance(call.kwargs["collected_data_json"], dict)
    chat.commit.assert_awaited()


@pytest.mark.asyncio
async def test_two_turn_flow_sets_then_fills_slot() -> None:
    bot = _make_bot(niche_id="education")
    conv = _make_conversation(bot, state=ConversationFlowState.start.value)
    chat, bots = _mock_repos(bot)
    orch = _orch(chat, bots, intent=ConversationDetectedIntent.sales_interest)

    r1 = await orch.process_sales_turn(bot, conv, "quote for tutoring", persist_user_message=False)
    assert r1.updated_collected_data.get(ORCH_TARGET_FIELD_KEY) == "student_grade"
    assert "student_grade" not in r1.updated_collected_data or not r1.updated_collected_data.get(
        "student_grade"
    )

    r2 = await orch.process_sales_turn(bot, conv, "9th grade", persist_user_message=False)
    assert r2.updated_collected_data.get("student_grade") == "Grade 9"
    assert r2.success is True
    assert r2.assistant_text is not None


@pytest.mark.parametrize(
    ("niche_id", "first_key", "user_msg", "expected_stored"),
    [
        ("education", "student_grade", "He is in grade 10", "Grade 10"),
        ("healthcare", "specialty", "Dentistry cleaning visit", "Dentistry cleaning visit"),
        (
            "dev_agency",
            "requested_solution",
            "Lead capture bot for our site",
            "Lead capture bot for our site",
        ),
        ("services", "service_type", "Kitchen sink leak repair", "Kitchen sink leak repair"),
    ],
)
@pytest.mark.asyncio
async def test_niche_basic_qualification_slot_progression(
    niche_id: str,
    first_key: str,
    user_msg: str,
    expected_stored: str,
) -> None:
    bot = _make_bot(niche_id=niche_id)
    conv = _make_conversation(
        bot,
        state=ConversationFlowState.qualification.value,
        collected={ORCH_TARGET_FIELD_KEY: first_key},
    )
    chat, bots = _mock_repos(bot)
    orch = _orch(chat, bots, intent=ConversationDetectedIntent.sales_interest)

    result = await orch.process_sales_turn(bot, conv, user_msg, persist_user_message=False)

    # Each niche now has a single required core field. Once it is filled, the orchestrator (which
    # runs the planner with ``collect_optional_core_fields=False``) marks qualification complete and
    # the state machine advances qualification → offer. No second core field is queued, so the
    # orchestrator clears its target-field key.
    assert result.updated_collected_data.get(first_key) == expected_stored
    assert ORCH_TARGET_FIELD_KEY not in result.updated_collected_data
    assert result.metadata.next_state == ConversationFlowState.offer.value


@pytest.mark.asyncio
async def test_dev_agency_channel_extractor_website() -> None:
    bot = _make_bot(niche_id="dev_agency")
    conv = _make_conversation(
        bot,
        state=ConversationFlowState.qualification.value,
        collected={ORCH_TARGET_FIELD_KEY: "website_or_bot_or_crm"},
    )
    chat, bots = _mock_repos(bot)
    orch = _orch(chat, bots, intent=ConversationDetectedIntent.sales_interest)

    result = await orch.process_sales_turn(
        bot,
        conv,
        "We need a new marketing website",
        persist_user_message=False,
    )

    assert result.updated_collected_data.get("website_or_bot_or_crm") == "website"


@pytest.mark.asyncio
async def test_offer_state_uses_offer_response_mode() -> None:
    bot = _make_bot(niche_id="education")
    conv = _make_conversation(
        bot,
        state=ConversationFlowState.qualification.value,
        collected={
            "student_grade": "Grade 9",
            "subject": "Math",
            "lesson_format": "online",
            "branch_or_location": "Main",
            "qualification_complete": True,
        },
    )
    chat, bots = _mock_repos(bot)
    orch = _orch(chat, bots, intent=ConversationDetectedIntent.sales_interest)

    result = await orch.process_sales_turn(bot, conv, "Sounds good so far", persist_user_message=False)

    assert result.metadata.next_state == ConversationFlowState.offer.value
    assert result.metadata.response_mode == ResponseMode.offer.value


# --- Safety / safeguard integration ---


@pytest.mark.asyncio
async def test_safeguard_very_long_input_skips_llm_polite_copy() -> None:
    bot = _make_bot(niche_id="education")
    conv = _make_conversation(
        bot,
        state=ConversationFlowState.qualification.value,
        collected={ORCH_TARGET_FIELD_KEY: "student_grade"},
    )
    chat, bots = _mock_repos(bot)
    stub = TrackingStubProvider("SHOULD_NOT_APPEAR")
    orch = _orch(chat, bots, provider=stub)

    long_text = "x" * (SALES_USER_HARD_MAX_CHARS + 1)
    result = await orch.process_sales_turn(bot, conv, long_text, persist_user_message=False)

    assert stub.generate_response_calls == 0
    assert result.success is True
    assert result.metadata.safeguard_reason_code == "safeguard_message_too_long"
    assert "SHOULD_NOT_APPEAR" not in (result.assistant_text or "")
    polite = (result.assistant_text or "").lower()
    assert "longer" in polite or "short" in polite


@pytest.mark.asyncio
async def test_safeguard_repeated_vague_fourth_turn_skips_llm() -> None:
    bot = _make_bot(niche_id="education")
    conv = _make_conversation(
        bot,
        state=ConversationFlowState.qualification.value,
        collected={ORCH_TARGET_FIELD_KEY: "student_grade"},
    )
    chat, bots = _mock_repos(bot)
    stub = TrackingStubProvider("LLM_REPLY")
    orch = _orch(chat, bots, provider=stub)

    for _ in range(3):
        await orch.process_sales_turn(bot, conv, "?", persist_user_message=False)
    assert stub.generate_response_calls == 3

    r4 = await orch.process_sales_turn(bot, conv, "?", persist_user_message=False)
    assert stub.generate_response_calls == 3
    assert r4.metadata.safeguard_reason_code == "safeguard_vague_repeated"
    assert r4.success is True
    assert "detail" in (r4.assistant_text or "").lower()


@pytest.mark.asyncio
async def test_safeguard_same_slot_miss_loop_fourth_turn_skips_llm() -> None:
    bot = _make_bot(niche_id="education")
    conv = _make_conversation(
        bot,
        state=ConversationFlowState.qualification.value,
        collected={ORCH_TARGET_FIELD_KEY: "student_grade"},
    )
    chat, bots = _mock_repos(bot)
    stub = TrackingStubProvider("LLM_REPLY")
    orch = _orch(chat, bots, provider=stub)

    for _ in range(3):
        await orch.process_sales_turn(bot, conv, "blue elephant sky", persist_user_message=False)
    assert stub.generate_response_calls == 3

    r4 = await orch.process_sales_turn(bot, conv, "blue elephant sky", persist_user_message=False)
    assert stub.generate_response_calls == 3
    assert r4.metadata.safeguard_reason_code == "safeguard_same_slot_loop"
    assert r4.success is True


@pytest.mark.asyncio
async def test_invalid_conversation_state_recoverable_success() -> None:
    bot = _make_bot(niche_id="education")
    conv = _make_conversation(bot, state="not_a_valid_funnel_state_xyz", collected={})
    chat, bots = _mock_repos(bot)
    stub = TrackingStubProvider()
    orch = _orch(chat, bots, provider=stub)

    result = await orch.process_sales_turn(
        bot,
        conv,
        "I want tutoring for my daughter",
        persist_user_message=False,
    )

    assert result.success is True
    assert result.metadata.previous_state == ConversationFlowState.fallback.value
    assert stub.generate_response_calls == 1
    assert result.updated_current_state in {s.value for s in ConversationFlowState}


@pytest.mark.asyncio
async def test_conversation_usable_after_safeguard_llm_resumes() -> None:
    bot = _make_bot(niche_id="education")
    conv = _make_conversation(
        bot,
        state=ConversationFlowState.qualification.value,
        collected={ORCH_TARGET_FIELD_KEY: "student_grade"},
    )
    chat, bots = _mock_repos(bot)
    stub = TrackingStubProvider("After safeguard reply.")
    orch = _orch(chat, bots, provider=stub)

    for _ in range(3):
        await orch.process_sales_turn(bot, conv, "?", persist_user_message=False)
    await orch.process_sales_turn(bot, conv, "?", persist_user_message=False)

    assert stub.generate_response_calls == 3

    r_ok = await orch.process_sales_turn(
        bot,
        conv,
        "She is in 9th grade",
        persist_user_message=False,
    )
    assert stub.generate_response_calls == 4
    assert r_ok.metadata.safeguard_reason_code is None
    assert r_ok.updated_collected_data.get("student_grade") == "Grade 9"
    assert r_ok.success is True


@pytest.mark.asyncio
async def test_nonsense_inputs_do_not_break_state_machine() -> None:
    """Semantically irrelevant but word-like replies must not crash; stay under vague/miss thresholds."""
    bot = _make_bot(niche_id="education")
    conv = _make_conversation(
        bot,
        state=ConversationFlowState.qualification.value,
        collected={ORCH_TARGET_FIELD_KEY: "student_grade"},
    )
    chat, bots = _mock_repos(bot)
    stub = TrackingStubProvider("ok")
    orch = _orch(chat, bots, provider=stub)

    # Two+ word-like tokens each (not "vague"); same slot missed < 4 times → LLM path each turn.
    messages = [
        "tropical storm alpha",
        "desert moon calendar",
        "quantum foam glitter",
    ]
    for msg in messages:
        r = await orch.process_sales_turn(bot, conv, msg, persist_user_message=False)
        assert r.success is True
        assert r.updated_current_state in {s.value for s in ConversationFlowState}
        assert r.metadata.safeguard_reason_code is None

    assert stub.generate_response_calls == 3


@pytest.mark.asyncio
async def test_trivial_greeting_sales_skips_intent_classifier_and_llm() -> None:
    bot = _make_bot(niche_id="generic")
    conv = _make_conversation(bot, state=ConversationFlowState.start.value)
    chat, bots = _mock_repos(bot)
    intent_mock = _intent_classifier_mock(ConversationDetectedIntent.sales_interest)
    provider = TrackingStubProvider("LLM would say this")
    settings = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "dummy",
            "ai_trivial_greeting_fast_path_enabled": True,
        }
    )

    def _res(_settings: Settings, _provider_id: str | None) -> AIProvider:
        return provider

    orch = SalesConversationOrchestrator(
        chat,
        bots,
        settings=settings,
        intent_classifier=intent_mock,
        provider_resolver=_res,
        lead_repo=_stub_lead_repo(),
        lead_owner_delivery=None,
    )
    result = await orch.process_sales_turn(bot, conv, "Hi", persist_user_message=False)
    assert result.success is True
    assert result.assistant_text
    assert "help" in (result.assistant_text or "").lower()
    intent_mock.classify.assert_not_called()
    assert provider.generate_response_calls == 0
