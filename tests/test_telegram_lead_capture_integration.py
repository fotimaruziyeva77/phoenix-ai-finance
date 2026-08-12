"""
Telegram-origin sales leads — PostgreSQL integration (real orchestrator + real CRM rows).

Exercises the same :class:`~app.services.sales_conversation_orchestrator.SalesConversationOrchestrator`
path as the widget, with ``Conversation.channel = telegram`` and ``telegram_chat_id`` set.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.lib.chat_channels import CONVERSATION_CHANNEL_TELEGRAM
from app.models.ai_foundation import Conversation
from app.models.bot import Bot
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.models.enums import UserRole
from app.models.lead import Lead
from app.models.user import User
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.bot_repository import BotRepository
from app.repositories.lead_event_repository import LeadEventRepository
from app.repositories.lead_repository import LeadListFilters, LeadRepository
from app.services.lead_event_service import LeadEventService
from app.services.lead_pipeline_service import LeadPipelineService
from app.services.sales_conversation_orchestrator import SalesConversationOrchestrator
from app.services.sales_lead_capture_turn import LEAD_CAPTURE_DONE_KEY
from sqlalchemy import func, select

from tests.integration_db import integration_database_url
from tests.test_sales_lead_capture_flow_integration import (
    TrackingStubProvider,
    _full_collected_ready_for_lead,
    _intent_classifier_mock,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _integration_db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _integration_db_url(),
        reason=(
            "Set TEST_DATABASE_URL (recommended) or host-reachable DATABASE_URL "
            "(not @postgres: — use 127.0.0.1 when testing from the host)."
        ),
    ),
]


def _alembic_upgrade_head(url: str) -> None:
    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        command.upgrade(cfg, "head")
    finally:
        if prev is not None:
            os.environ["DATABASE_URL"] = prev
        else:
            os.environ.pop("DATABASE_URL", None)
        get_settings.cache_clear()


@pytest.fixture(scope="module", autouse=True)
def _alembic_head() -> None:
    u = _integration_db_url()
    assert u is not None
    _alembic_upgrade_head(u)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def _unique_email(prefix: str = "tg-lead") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _education_collected_telegram() -> dict[str, object]:
    """Closing-ready slots plus realistic Telegram adapter hints."""
    data = _full_collected_ready_for_lead("education")
    data["telegram_username"] = "visitor_edu"
    data["telegram_first_name"] = "Taylor"
    return data


def _make_orchestrator(chat: AIChatRepository, bots: BotRepository) -> SalesConversationOrchestrator:
    def _resolve_stub(_settings, _provider_id=None):
        return TrackingStubProvider()

    return SalesConversationOrchestrator(
        chat,
        bots,
        settings=get_settings(),
        intent_classifier=_intent_classifier_mock(ConversationDetectedIntent.sales_interest),
        provider_resolver=_resolve_stub,
        lead_owner_delivery=None,
    )


def test_telegram_thread_creates_lead_source_channel_scoring_summary_and_crm_list(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    1. Telegram conversation can create a lead
    2. source_channel = telegram
    3. score and summary populated (shared pipeline)
    5. Lead appears in owner CRM list with source_channel
    """

    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        tg_chat_id = 8800110022
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("own"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Telegram Sales Bot",
                    niche_id="education",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                conv = Conversation(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    channel=CONVERSATION_CHANNEL_TELEGRAM,
                    status="active",
                    telegram_chat_id=tg_chat_id,
                    current_state=ConversationFlowState.closing.value,
                    niche_id_snapshot="education",
                    collected_data_json=_education_collected_telegram(),
                )
                session.add(conv)
                await session.commit()
                oid, bid, cid = owner.id, bot.id, conv.id

            async with sm() as session:
                chat = AIChatRepository(session)
                bots = BotRepository(session)
                conv_row = await session.get(Conversation, cid)
                bot_row = await session.get(Bot, bid)
                owner_row = await session.get(User, oid)
                assert conv_row is not None and bot_row is not None and owner_row is not None

                orch = _make_orchestrator(chat, bots)
                result = await orch.process_sales_turn(
                    bot_row,
                    conv_row,
                    "Yes, please finalize everything on your side.",
                    owner_user=owner_row,
                    persist_user_message=True,
                )

                assert result.success
                assert result.metadata.lead_capture_created is True
                assert result.metadata.lead_capture_lead_id is not None

                lead = (
                    await session.execute(select(Lead).where(Lead.conversation_id == cid))
                ).scalar_one()
                assert lead.source_channel == CONVERSATION_CHANNEL_TELEGRAM
                assert lead.phone == "+15550123456"
                assert lead.lead_score is not None
                assert 0 <= lead.lead_score <= 100
                assert lead.summary is not None
                assert len((lead.summary or "").strip()) > 0
                assert lead.collected_data_json is not None
                assert lead.collected_data_json.get("telegram_username") == "visitor_edu"

                lr = LeadRepository(session)
                pipeline = LeadPipelineService(lr, LeadEventService(LeadEventRepository(session)))
                listing = await pipeline.list_leads_for_owner(
                    owner_row,
                    filters=LeadListFilters(bot_id=bid),
                    limit=20,
                    offset=0,
                )
                assert listing.total >= 1
                match = [x for x in listing.items if x.id == lead.id]
                assert len(match) == 1
                assert match[0].source_channel == CONVERSATION_CHANNEL_TELEGRAM
                assert match[0].lead_score == lead.lead_score
                assert match[0].summary == lead.summary
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_telegram_same_thread_second_turn_no_duplicate_lead(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """4. Same conversation_id cannot create a second lead after capture flag is set."""

    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        tg_chat_id = 7700330044
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("dupc"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="TG Dup Conv Bot",
                    niche_id="education",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                conv = Conversation(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    channel=CONVERSATION_CHANNEL_TELEGRAM,
                    status="active",
                    telegram_chat_id=tg_chat_id,
                    current_state=ConversationFlowState.closing.value,
                    niche_id_snapshot="education",
                    collected_data_json=_education_collected_telegram(),
                )
                session.add(conv)
                await session.commit()
                oid, bid, cid = owner.id, bot.id, conv.id

            async with sm() as session:
                chat = AIChatRepository(session)
                bots = BotRepository(session)
                orch = _make_orchestrator(chat, bots)

                conv_row = await session.get(Conversation, cid)
                bot_row = await session.get(Bot, bid)
                owner_row = await session.get(User, oid)
                assert conv_row and bot_row and owner_row

                r1 = await orch.process_sales_turn(
                    bot_row,
                    conv_row,
                    "Yes, finalize now.",
                    owner_user=owner_row,
                    persist_user_message=True,
                )
                assert r1.metadata.lead_capture_created is True

                await session.refresh(conv_row)
                assert conv_row.collected_data_json.get(LEAD_CAPTURE_DONE_KEY) is True

                n_after_first = (
                    await session.execute(
                        select(func.count()).select_from(Lead).where(Lead.conversation_id == cid),
                    )
                ).scalar_one()
                assert int(n_after_first) == 1

                r2 = await orch.process_sales_turn(
                    bot_row,
                    conv_row,
                    "Thanks, bye!",
                    owner_user=owner_row,
                    persist_user_message=True,
                )
                assert r2.metadata.lead_capture_created is False

                n_after_second = (
                    await session.execute(
                        select(func.count()).select_from(Lead).where(Lead.conversation_id == cid),
                    )
                ).scalar_one()
                assert int(n_after_second) == 1
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_telegram_second_thread_same_phone_blocked_by_open_pipeline_duplicate_rule(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Two Telegram chats (different ``telegram_chat_id``), same bot, same normalized phone in slots.
    Second thread must not insert another lead while the first remains in an open pipeline status.
    """

    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("dupp"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="TG Dup Phone Bot",
                    niche_id="education",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                base = _education_collected_telegram()
                c1 = Conversation(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    channel=CONVERSATION_CHANNEL_TELEGRAM,
                    status="active",
                    telegram_chat_id=6600110011,
                    current_state=ConversationFlowState.closing.value,
                    niche_id_snapshot="education",
                    collected_data_json=dict(base),
                )
                c2 = Conversation(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    channel=CONVERSATION_CHANNEL_TELEGRAM,
                    status="active",
                    telegram_chat_id=6600220022,
                    current_state=ConversationFlowState.closing.value,
                    niche_id_snapshot="education",
                    collected_data_json=dict(base),
                )
                session.add_all([c1, c2])
                await session.commit()
                oid, bid = owner.id, bot.id
                id1, id2 = c1.id, c2.id

            async with sm() as session:
                chat = AIChatRepository(session)
                bots = BotRepository(session)
                orch = _make_orchestrator(chat, bots)
                owner_row = await session.get(User, oid)
                bot_row = await session.get(Bot, bid)
                assert owner_row and bot_row

                conv1 = await session.get(Conversation, id1)
                conv2 = await session.get(Conversation, id2)
                assert conv1 and conv2

                r1 = await orch.process_sales_turn(
                    bot_row,
                    conv1,
                    "Finalize my tutoring request.",
                    owner_user=owner_row,
                    persist_user_message=True,
                )
                assert r1.metadata.lead_capture_created is True

                r2 = await orch.process_sales_turn(
                    bot_row,
                    conv2,
                    "Please finalize this one too.",
                    owner_user=owner_row,
                    persist_user_message=True,
                )
                assert r2.metadata.lead_capture_created is False

                total_for_bot = (
                    await session.execute(
                        select(func.count()).select_from(Lead).where(Lead.bot_id == bid),
                    )
                ).scalar_one()
                assert int(total_for_bot) == 1
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())
