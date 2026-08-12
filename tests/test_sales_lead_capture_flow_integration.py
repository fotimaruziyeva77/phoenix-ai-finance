"""
Lead capture integration in the sales orchestrator (all four niches).

Uses mocked chat/bot repos and a stateful in-memory lead repo; exercises real planner,
state machine, lead gates, and capture branch (closing / confirmation text, metadata flags).
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.ai_providers.base import AIProvider
from app.ai_providers.types import GenerateParams, NormalizedAIResult, TokenUsage
from app.core.config import Settings, get_settings
from app.lib.chat_channels import CONVERSATION_CHANNEL_TELEGRAM, CONVERSATION_CHANNEL_WEB_WIDGET
from app.models.ai_foundation import Conversation
from app.models.bot import Bot
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.bot_repository import BotRepository
from app.services.intent_types import IntentClassificationResult
from app.services.sales_conversation_orchestrator import ORCH_TARGET_FIELD_KEY, SalesConversationOrchestrator
from app.services.sales_lead_capture_turn import CAPTURED_LEAD_ID_KEY, LEAD_CAPTURE_DONE_KEY


class TrackingStubProvider(AIProvider):
    """Counts LLM invocations (lead-capture path must skip the model)."""

    def __init__(self, reply_text: str = "Model says hello.") -> None:
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
            tokens=TokenUsage(input_tokens=2, output_tokens=3, total_tokens=5),
        )

    def parse_usage(self, raw: dict[str, Any] | None) -> TokenUsage | None:
        return None

    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        return ("stub_error", str(exc))

    async def aclose(self) -> None:
        return None


class StatefulLeadRepo:
    """Minimal lead persistence for integration tests (matches call shape of ``LeadRepository``)."""

    def __init__(self) -> None:
        self.create_calls: list[dict[str, object]] = []
        self.get_lead_calls = 0
        self._by_conversation: dict[uuid.UUID, SimpleNamespace] = {}
        self.session = MagicMock()
        self.session.flush = AsyncMock()
        self.session.add = MagicMock()
        self.session.refresh = AsyncMock()

    async def get_lead_by_conversation_id(self, conversation_id: uuid.UUID) -> SimpleNamespace | None:
        self.get_lead_calls += 1
        return self._by_conversation.get(conversation_id)

    async def find_open_lead_same_normalized_phone(self, **kwargs: object) -> None:
        return None

    async def count_leads_same_phone_recent(self, **kwargs: object) -> int:
        return 0

    async def create_lead(self, **kwargs: object) -> SimpleNamespace:
        self.create_calls.append(dict(kwargs))
        cid = kwargs["conversation_id"]
        assert isinstance(cid, uuid.UUID)
        row = SimpleNamespace(id=uuid.uuid4(), **kwargs)
        self._by_conversation[cid] = row
        return row


def _make_bot(*, niche_id: str) -> Bot:
    oid = uuid.uuid4()
    return Bot(
        id=uuid.uuid4(),
        owner_id=oid,
        name="Niche Test Bot",
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
        niche_id_snapshot=bot.niche_id,
        channel="web_chat",
    )


def _owner(bot: Bot) -> SimpleNamespace:
    return SimpleNamespace(id=bot.owner_id)


def _intent_classifier_mock(intent: ConversationDetectedIntent) -> MagicMock:
    m = MagicMock()
    m.classify = AsyncMock(
        return_value=IntentClassificationResult(intent=intent, confidence=0.95, source="rules")
    )
    return m


def _mock_repos(bot: Bot) -> tuple[MagicMock, MagicMock]:
    chat = MagicMock(spec=AIChatRepository)
    chat.session = MagicMock()
    chat.list_recent_history_messages = AsyncMock(return_value=[])
    chat.add_message = AsyncMock(side_effect=lambda **kwargs: SimpleNamespace(id=uuid.uuid4()))
    chat.update_conversation_sales_flow = AsyncMock()
    chat.touch_conversation_updated_at = AsyncMock()
    chat.commit = AsyncMock()
    chat.rollback = AsyncMock()
    bots = MagicMock(spec=BotRepository)
    bots.get_bot_by_id = AsyncMock(return_value=bot)
    return chat, bots


def _full_collected_ready_for_lead(niche_id: str) -> dict[str, object]:
    """
    Slots + funnel flags so one transition moves closing → completed; phone present for CRM gate.
    """
    data: dict[str, object] = {
        "qualification_complete": True,
        "accept_offer": True,
        "deal_finalized": True,
        "phone": "+15550123456",
    }
    if niche_id == "education":
        data.update({"student_grade": "Grade 9", "subject": "Mathematics"})
    elif niche_id == "healthcare":
        data.update({"specialty": "Dentistry", "appointment_type": "cleaning"})
    elif niche_id == "dev_agency":
        data.update(
            {
                "requested_solution": "Lead capture chatbot for marketing site",
                "website_or_bot_or_crm": "chatbot",
            }
        )
    elif niche_id == "services":
        data.update({"service_type": "plumbing repair", "location": "Downtown Chicago"})
    else:
        raise ValueError(niche_id)
    return data


def _opening_message_for_niche(niche_id: str) -> str:
    return {
        "education": "I need math tutoring quote for grade 9",
        "healthcare": "I want to book a dental cleaning visit",
        "dev_agency": "We need a lead capture bot for our website",
        "services": "Kitchen sink is leaking, need a plumber in Chicago",
    }[niche_id]


def _orch_with_lead_repo(
    chat: MagicMock,
    bots: MagicMock,
    lead_repo: StatefulLeadRepo,
    *,
    intent: ConversationDetectedIntent = ConversationDetectedIntent.sales_interest,
    provider: AIProvider | None = None,
    lead_owner_delivery: Any | None = None,
) -> SalesConversationOrchestrator:
    if provider is not None:

        def _resolve(_settings: Settings, _provider_id: str | None) -> AIProvider:
            return provider

        resolver: Callable[[Settings, str | None], AIProvider] = _resolve
    else:

        def _resolve2(_settings: Settings, _provider_id: str | None) -> AIProvider:
            return TrackingStubProvider()

        resolver = _resolve2

    return SalesConversationOrchestrator(
        chat,
        bots,
        settings=get_settings(),
        intent_classifier=_intent_classifier_mock(intent),
        provider_resolver=resolver,
        lead_repo=lead_repo,
        lead_owner_delivery=lead_owner_delivery,
    )


def _apply_turn(conv: Conversation, result: Any) -> None:
    conv.current_state = result.updated_current_state
    conv.collected_data_json = dict(result.updated_collected_data)
    if result.metadata.detected_intent:
        conv.detected_intent = result.metadata.detected_intent


@pytest.mark.parametrize("niche_id", ("education", "healthcare", "dev_agency", "services"))
def test_conversation_progresses_without_early_lead_creation(niche_id: str) -> None:
    """Qualification-style turn: funnel not at closing/completed → no lead row, gates not satisfied."""

    async def run() -> None:
        bot = _make_bot(niche_id=niche_id)
        conv = _make_conversation(
            bot,
            state=ConversationFlowState.qualification.value,
            collected={ORCH_TARGET_FIELD_KEY: "phone"},
        )
        chat, bots = _mock_repos(bot)
        lead_repo = StatefulLeadRepo()
        stub = TrackingStubProvider()
        orch = _orch_with_lead_repo(chat, bots, lead_repo, provider=stub)

        result = await orch.process_sales_turn(
            bot,
            conv,
            "+1 555 999 0001",
            owner_user=_owner(bot),
            persist_user_message=False,
        )

        assert result.metadata.lead_capture_created is False
        assert len(lead_repo.create_calls) == 0
        assert stub.generate_response_calls == 1

    asyncio.run(run())


@pytest.mark.parametrize("niche_id", ("education", "healthcare", "dev_agency", "services"))
def test_lead_created_once_at_closing_completed_threshold(niche_id: str) -> None:
    """Seeded closing + finalized deal + full slots → one insert, metadata flags, closing copy, no LLM."""

    async def run() -> None:
        bot = _make_bot(niche_id=niche_id)
        collected = _full_collected_ready_for_lead(niche_id)
        conv = _make_conversation(bot, state=ConversationFlowState.closing.value, collected=collected)
        chat, bots = _mock_repos(bot)
        lead_repo = StatefulLeadRepo()
        stub = TrackingStubProvider()
        orch = _orch_with_lead_repo(chat, bots, lead_repo, provider=stub)

        result = await orch.process_sales_turn(
            bot,
            conv,
            "Yes, please finalize everything on your side.",
            owner_user=_owner(bot),
            persist_user_message=False,
        )

        assert result.metadata.next_state == ConversationFlowState.completed.value
        assert result.metadata.lead_capture_created is True
        assert result.metadata.lead_capture_lead_id is not None
        assert len(lead_repo.create_calls) == 1
        assert lead_repo.create_calls[0]["conversation_id"] == conv.id
        assert result.updated_collected_data.get(LEAD_CAPTURE_DONE_KEY) is True
        assert result.updated_collected_data.get(CAPTURED_LEAD_ID_KEY)
        assert stub.generate_response_calls == 0
        assert result.assistant_text
        assert "Thank you" in result.assistant_text
        assert "follow up" in result.assistant_text.lower()

    asyncio.run(run())


@pytest.mark.parametrize("niche_id", ("education", "healthcare", "dev_agency", "services"))
@pytest.mark.parametrize(
    "ingress_channel",
    (CONVERSATION_CHANNEL_WEB_WIDGET, CONVERSATION_CHANNEL_TELEGRAM),
)
def test_lead_source_channel_matches_conversation_ingress(niche_id: str, ingress_channel: str) -> None:
    """CRM segmentation: same capture path, ``source_channel`` from ``Conversation.channel``."""

    async def run() -> None:
        bot = _make_bot(niche_id=niche_id)
        collected = _full_collected_ready_for_lead(niche_id)
        conv = _make_conversation(bot, state=ConversationFlowState.closing.value, collected=collected)
        conv.channel = ingress_channel
        chat, bots = _mock_repos(bot)
        lead_repo = StatefulLeadRepo()
        stub = TrackingStubProvider()
        orch = _orch_with_lead_repo(chat, bots, lead_repo, provider=stub)

        result = await orch.process_sales_turn(
            bot,
            conv,
            "Yes, please finalize everything on your side.",
            owner_user=_owner(bot),
            persist_user_message=False,
        )

        assert result.metadata.lead_capture_created is True
        assert len(lead_repo.create_calls) == 1
        assert lead_repo.create_calls[0]["source_channel"] == ingress_channel

    asyncio.run(run())


@pytest.mark.parametrize("niche_id", ("education", "healthcare", "dev_agency", "services"))
def test_lead_not_duplicated_on_second_turn(niche_id: str) -> None:
    async def run() -> None:
        bot = _make_bot(niche_id=niche_id)
        collected = _full_collected_ready_for_lead(niche_id)
        conv = _make_conversation(bot, state=ConversationFlowState.closing.value, collected=collected)
        chat, bots = _mock_repos(bot)
        lead_repo = StatefulLeadRepo()
        stub = TrackingStubProvider()
        orch = _orch_with_lead_repo(chat, bots, lead_repo, provider=stub)

        r1 = await orch.process_sales_turn(
            bot,
            conv,
            "Please finalize.",
            owner_user=_owner(bot),
            persist_user_message=False,
        )
        assert r1.metadata.lead_capture_created is True
        assert len(lead_repo.create_calls) == 1

        _apply_turn(conv, r1)
        stub.generate_response_calls = 0

        r2 = await orch.process_sales_turn(
            bot,
            conv,
            "Thanks again!",
            owner_user=_owner(bot),
            persist_user_message=False,
        )

        assert len(lead_repo.create_calls) == 1
        assert r2.metadata.lead_capture_created is False
        assert r2.updated_collected_data.get(LEAD_CAPTURE_DONE_KEY) is True

    asyncio.run(run())


@pytest.mark.parametrize("niche_id", ("education", "healthcare", "dev_agency", "services"))
def test_telegram_notify_called_once_when_configured(niche_id: str) -> None:
    async def run() -> None:
        bot = _make_bot(niche_id=niche_id)
        collected = _full_collected_ready_for_lead(niche_id)
        conv = _make_conversation(bot, state=ConversationFlowState.closing.value, collected=collected)
        chat, bots = _mock_repos(bot)
        lead_repo = StatefulLeadRepo()
        stub = TrackingStubProvider()
        delivery = MagicMock()
        delivery.route_new_lead_after_commit = AsyncMock()
        orch = _orch_with_lead_repo(chat, bots, lead_repo, provider=stub, lead_owner_delivery=delivery)

        await orch.process_sales_turn(
            bot,
            conv,
            "Finalize please.",
            owner_user=_owner(bot),
            persist_user_message=False,
        )

        delivery.route_new_lead_after_commit.assert_awaited_once()
        kw = delivery.route_new_lead_after_commit.await_args.kwargs
        assert kw["owner_id"] == bot.owner_id
        assert kw["bot"] is bot
        assert kw["lead"] is not None

    asyncio.run(run())


def test_lead_capture_succeeds_when_telegram_service_absent() -> None:
    """No :class:`~app.services.lead_owner_delivery_router.LeadOwnerDeliveryRouter` must not block persistence."""

    async def run() -> None:
        bot = _make_bot(niche_id="education")
        collected = _full_collected_ready_for_lead("education")
        conv = _make_conversation(bot, state=ConversationFlowState.closing.value, collected=collected)
        chat, bots = _mock_repos(bot)
        lead_repo = StatefulLeadRepo()
        orch = _orch_with_lead_repo(chat, bots, lead_repo, lead_owner_delivery=None)

        result = await orch.process_sales_turn(
            bot,
            conv,
            "Finalize.",
            owner_user=_owner(bot),
            persist_user_message=False,
        )

        assert result.metadata.lead_capture_created is True
        assert len(lead_repo.create_calls) == 1

    asyncio.run(run())


def test_multi_turn_realistic_education_flow_no_lead_until_late_funnel() -> None:
    """Start → qualification fills; still no lead until closing/completed threshold."""

    async def run() -> None:
        bot = _make_bot(niche_id="education")
        conv = _make_conversation(bot, state=ConversationFlowState.start.value, collected={})
        chat, bots = _mock_repos(bot)
        lead_repo = StatefulLeadRepo()
        stub = TrackingStubProvider("Ack.")
        orch = _orch_with_lead_repo(chat, bots, lead_repo, provider=stub)

        r1 = await orch.process_sales_turn(
            bot,
            conv,
            _opening_message_for_niche("education"),
            owner_user=_owner(bot),
            persist_user_message=False,
        )
        assert r1.metadata.lead_capture_created is False
        assert len(lead_repo.create_calls) == 0
        _apply_turn(conv, r1)

        conv.collected_data_json["student_grade"] = "Grade 9"
        conv.collected_data_json["subject"] = "Math"
        conv.collected_data_json["qualification_complete"] = True
        conv.collected_data_json["accept_offer"] = True
        conv.current_state = ConversationFlowState.offer.value

        r2 = await orch.process_sales_turn(
            bot,
            conv,
            "We accept your proposal — please move forward.",
            owner_user=_owner(bot),
            persist_user_message=False,
        )
        assert r2.metadata.lead_capture_created is False
        assert len(lead_repo.create_calls) == 0
        _apply_turn(conv, r2)

        assert conv.current_state == ConversationFlowState.closing.value
        conv.collected_data_json["phone"] = "+15559876543"
        conv.collected_data_json["deal_finalized"] = True

        r3 = await orch.process_sales_turn(
            bot,
            conv,
            "Please close this out.",
            owner_user=_owner(bot),
            persist_user_message=False,
        )
        assert r3.metadata.lead_capture_created is True
        assert len(lead_repo.create_calls) == 1
        assert r3.updated_collected_data.get(LEAD_CAPTURE_DONE_KEY) is True

    asyncio.run(run())
