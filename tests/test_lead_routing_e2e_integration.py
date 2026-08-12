"""
End-to-end lead routing integration: **web_widget** sales capture → CRM row → owner delivery → timeline.

**Notification test strategy**

* **Real:** PostgreSQL, :class:`~app.services.sales_conversation_orchestrator.SalesConversationOrchestrator`,
  lead insert, :class:`~app.services.lead_owner_delivery_router.LeadOwnerDeliveryRouter`, and
  ``Lead`` / ``LeadEvent`` persistence.
* **Faked (outer boundary only):** ``httpx.MockTransport`` replaces Telegram Bot API ``sendMessage``.
  Target chat/token come from :class:`~tests.lead_routing_integration_support.FixedTelegramSendTargetProvider`
  so tests do not require a live ``telegram_configs`` row.
* **Observability:** Assertions use ``Lead.owner_inbox_routed_at``, ``Lead.telegram_delivery_status``,
  ``Lead.telegram_delivery_attempts``, and append-only ``lead_events`` types
  (``lead_created``, ``system_action``, ``notification_delivered`` / ``notification_failed``).

**No silent loss**

* After capture, the lead row must exist regardless of Telegram outcome.
* When delivery runs, inbox routing is stamped and timeline rows prove dashboard + notify phases.
* Telegram failure still leaves the lead in ``GET /api/v1/leads`` with ``notification_failed`` on the timeline.
"""

from __future__ import annotations

import asyncio
import uuid

import httpx
import pytest
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.integrations.telegram.lead_alert_types import TelegramSendTarget
from app.lib.chat_channels import CONVERSATION_CHANNEL_WEB_WIDGET
from app.main import app
from app.models.ai_foundation import Conversation
from app.models.bot import Bot
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.models.enums import UserRole
from app.models.lead import Lead
from app.models.lead_event import LeadEvent
from app.models.user import User
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.bot_repository import BotRepository
from app.services.sales_conversation_orchestrator import SalesConversationOrchestrator
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.integration_db import integration_database_url
from tests.lead_routing_integration_support import (
    alembic_upgrade_head,
    fetch_lead_event_types,
    make_orchestrator_with_delivery,
    mock_telegram_send_message_transport,
)
from tests.test_sales_lead_capture_flow_integration import (
    TrackingStubProvider,
    _full_collected_ready_for_lead,
    _intent_classifier_mock,
)

JWT_ROUTING_E2E = "q" * 32


def _integration_db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _integration_db_url(),
        reason=(
            "Set TEST_DATABASE_URL or host-reachable DATABASE_URL "
            "(not @postgres: from the host)."
        ),
    ),
]


@pytest.fixture(scope="module", autouse=True)
def _alembic_for_lead_routing_e2e() -> None:
    u = _integration_db_url()
    assert u is not None
    alembic_upgrade_head(u)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def _auth_bearer(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _unique_email(prefix: str = "route-e2e") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def test_web_widget_qualified_lead_crm_delivery_and_timeline_success(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Widget-origin conversation → lead row → inbox stamp → Telegram OK → CRM events."""

    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        transport = mock_telegram_send_message_transport(status_code=200, ok=True)
        target = TelegramSendTarget(bot_token="MOCK_ROUTING_TOK", chat_id="556677")
        visitor_key = "w" * 32
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("w-owner"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Widget Routing Bot",
                    niche_id="education",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                conv = Conversation(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    channel=CONVERSATION_CHANNEL_WEB_WIDGET,
                    status="active",
                    public_visitor_session_key=visitor_key,
                    current_state=ConversationFlowState.closing.value,
                    niche_id_snapshot="education",
                    collected_data_json=_full_collected_ready_for_lead("education"),
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
                assert conv_row and bot_row and owner_row

                def _resolve_stub(_settings, _provider_id=None):
                    return TrackingStubProvider()

                async with httpx.AsyncClient(transport=transport) as http_client:
                    orch = await make_orchestrator_with_delivery(
                        chat_repo=chat,
                        bot_repo=bots,
                        settings=get_settings(),
                        intent_classifier=_intent_classifier_mock(ConversationDetectedIntent.sales_interest),
                        provider_resolver=_resolve_stub,
                        http_client=http_client,
                        telegram_target=target,
                    )
                    result = await orch.process_sales_turn(
                        bot_row,
                        conv_row,
                        "Yes — please finalize my tutoring lead now.",
                        owner_user=owner_row,
                        persist_user_message=True,
                    )

                assert result.success
                assert result.metadata.lead_capture_created is True
                assert result.metadata.lead_capture_lead_id is not None

                lead = (
                    await session.execute(select(Lead).where(Lead.conversation_id == cid))
                ).scalar_one()
                assert lead.source_channel == CONVERSATION_CHANNEL_WEB_WIDGET
                assert lead.phone == "+15550123456"
                assert lead.owner_inbox_routed_at is not None
                assert lead.telegram_delivery_status == "delivered"
                assert lead.telegram_delivery_attempts >= 1
                assert lead.telegram_delivery_updated_at is not None

                types = await fetch_lead_event_types(session, lead.id)
                assert "lead_created" in types
                assert "system_action" in types
                assert "notification_delivered" in types

                nf = (
                    await session.execute(
                        select(LeadEvent).where(
                            LeadEvent.lead_id == lead.id,
                            LeadEvent.event_type == "notification_delivered",
                        )
                    )
                ).scalar_one()
                meta = nf.metadata_json or {}
                assert meta.get("channel") == "telegram"
                assert int(meta.get("attempts") or 0) >= 1
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_web_widget_telegram_failure_lead_remains_with_notification_failed_event(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Outer delivery failure must not delete the CRM lead; timeline records ``notification_failed``."""

    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()

        def _fail_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"ok": False, "description": "fail"})

        transport = httpx.MockTransport(_fail_handler)
        target = TelegramSendTarget(bot_token="MOCK_FAIL_TOK", chat_id="889900")
        visitor_key = "v" * 32
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("fail-w"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Widget Fail Bot",
                    niche_id="education",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                conv = Conversation(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    channel=CONVERSATION_CHANNEL_WEB_WIDGET,
                    status="active",
                    public_visitor_session_key=visitor_key,
                    current_state=ConversationFlowState.closing.value,
                    niche_id_snapshot="education",
                    collected_data_json=_full_collected_ready_for_lead("education"),
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
                assert conv_row and bot_row and owner_row

                def _resolve_stub(_settings, _provider_id=None):
                    return TrackingStubProvider()

                async with httpx.AsyncClient(transport=transport) as http_client:
                    orch = await make_orchestrator_with_delivery(
                        chat_repo=chat,
                        bot_repo=bots,
                        settings=get_settings(),
                        intent_classifier=_intent_classifier_mock(ConversationDetectedIntent.sales_interest),
                        provider_resolver=_resolve_stub,
                        http_client=http_client,
                        telegram_target=target,
                    )
                    await orch.process_sales_turn(
                        bot_row,
                        conv_row,
                        "Finalize the lead please.",
                        owner_user=owner_row,
                        persist_user_message=True,
                    )

                lead = (
                    await session.execute(select(Lead).where(Lead.conversation_id == cid))
                ).scalar_one()
                assert lead.owner_inbox_routed_at is not None
                assert lead.telegram_delivery_status == "failed"

                types = await fetch_lead_event_types(session, lead.id)
                assert "lead_created" in types
                assert "notification_failed" in types
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_owner_rest_api_lists_lead_and_timeline_after_widget_capture(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP inbox + ``/events`` must match the same persisted lead as the orchestrator (no silent drop)."""

    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_ROUTING_E2E)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())

    access_token: str | None = None
    owner_id: uuid.UUID | None = None
    bot_id: uuid.UUID | None = None
    lead_id: uuid.UUID | None = None

    with TestClient(app) as client:
        reg = client.post(
            "/api/v1/auth/register",
            json={
                "email": _unique_email("http-owner"),
                "password": "password123",
                "full_name": "Lead routing HTTP",
            },
        )
        assert reg.status_code == 201, reg.text
        body = reg.json()
        access_token = body["access_token"]
        assert access_token
        owner_id = uuid.UUID(body["user"]["id"])

        bot_resp = client.post(
            "/api/v1/bots",
            headers=_auth_bearer(access_token),
            json={
                "name": "HTTP Widget Sales Bot",
                "niche_id": "education",
                "goal_type": "sales",
                "initial_channel": "web",
            },
        )
        assert bot_resp.status_code == 201, bot_resp.text
        bot_id = uuid.UUID(bot_resp.json()["id"])

        w = client.get(f"/api/v1/bots/{bot_id}/widget", headers=_auth_bearer(access_token))
        assert w.status_code == 200, w.text
        _ = w.json()["public_widget_key"]

    async def run_capture() -> None:
        nonlocal lead_id
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        transport = mock_telegram_send_message_transport()
        target = TelegramSendTarget(bot_token="HTTP_MOCK_TOK", chat_id="334455")
        visitor_key = "h" * 32
        sm = get_session_maker()
        async with sm() as session:
            conv = Conversation(
                bot_id=bot_id,
                owner_id=owner_id,
                channel=CONVERSATION_CHANNEL_WEB_WIDGET,
                status="active",
                public_visitor_session_key=visitor_key,
                current_state=ConversationFlowState.closing.value,
                niche_id_snapshot="education",
                collected_data_json=_full_collected_ready_for_lead("education"),
            )
            session.add(conv)
            await session.commit()
            await session.refresh(conv)
            cid = conv.id

        async with sm() as session:
            chat = AIChatRepository(session)
            bots = BotRepository(session)
            conv_row = await session.get(Conversation, cid)
            bot_row = await session.get(Bot, bot_id)
            owner_row = await session.get(User, owner_id)
            assert conv_row and bot_row and owner_row

            def _resolve_stub(_settings, _provider_id=None):
                return TrackingStubProvider()

            async with httpx.AsyncClient(transport=transport) as http_client:
                orch = await make_orchestrator_with_delivery(
                    chat_repo=chat,
                    bot_repo=bots,
                    settings=get_settings(),
                    intent_classifier=_intent_classifier_mock(ConversationDetectedIntent.sales_interest),
                    provider_resolver=_resolve_stub,
                    http_client=http_client,
                    telegram_target=target,
                )
                res = await orch.process_sales_turn(
                    bot_row,
                    conv_row,
                    "Please finalize everything.",
                    owner_user=owner_row,
                    persist_user_message=True,
                )
            assert res.metadata.lead_capture_created is True
            lead = (await session.execute(select(Lead).where(Lead.conversation_id == cid))).scalar_one()
            lead_id = lead.id

    asyncio.run(run_capture())

    try:
        with TestClient(app) as client:
            listed = client.get("/api/v1/leads", headers=_auth_bearer(access_token))
            assert listed.status_code == 200, listed.text
            payload = listed.json()
            assert payload["total"] >= 1
            ids = {item["id"] for item in payload["items"]}
            assert str(lead_id) in ids
            match = next(x for x in payload["items"] if x["id"] == str(lead_id))
            assert match["source_channel"] == CONVERSATION_CHANNEL_WEB_WIDGET
            assert match["owner_inbox_routed_at"] is not None
            assert match["telegram_delivery_status"] == "delivered"

            ev = client.get(
                f"/api/v1/leads/{lead_id}/events",
                headers=_auth_bearer(access_token),
            )
            assert ev.status_code == 200, ev.text
            etypes = {e["event_type"] for e in ev.json()["items"]}
            assert "lead_created" in etypes
            assert "notification_delivered" in etypes
    finally:
        asyncio.run(dispose_engine())
        get_settings.cache_clear()


def test_capture_without_delivery_router_lead_still_in_crm_no_inbox_stamp(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If ``lead_owner_delivery`` is not wired (misconfiguration), lead still persists — not silently dropped."""

    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        visitor_key = "n" * 32
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("no-del"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="No Delivery Bot",
                    niche_id="education",
                    goal_type="sales",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                conv = Conversation(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    channel=CONVERSATION_CHANNEL_WEB_WIDGET,
                    status="active",
                    public_visitor_session_key=visitor_key,
                    current_state=ConversationFlowState.closing.value,
                    niche_id_snapshot="education",
                    collected_data_json=_full_collected_ready_for_lead("education"),
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
                assert conv_row and bot_row and owner_row

                def _resolve_stub(_settings, _provider_id=None):
                    return TrackingStubProvider()

                orch = SalesConversationOrchestrator(
                    chat,
                    bots,
                    settings=get_settings(),
                    intent_classifier=_intent_classifier_mock(ConversationDetectedIntent.sales_interest),
                    provider_resolver=_resolve_stub,
                    lead_owner_delivery=None,
                )
                await orch.process_sales_turn(
                    bot_row,
                    conv_row,
                    "Finalize now.",
                    owner_user=owner_row,
                    persist_user_message=True,
                )

                lead = (
                    await session.execute(select(Lead).where(Lead.conversation_id == cid))
                ).scalar_one()
                assert lead.source_channel == CONVERSATION_CHANNEL_WEB_WIDGET
                assert lead.owner_inbox_routed_at is None
                assert lead.telegram_delivery_status is None
                types = await fetch_lead_event_types(session, lead.id)
                assert "lead_created" in types
                assert "notification_delivered" not in types
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())
