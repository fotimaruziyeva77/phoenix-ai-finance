"""
New-lead owner delivery router — PostgreSQL integration (dashboard stamp, Telegram, CRM events).

Exercises :class:`~app.services.lead_owner_delivery_router.LeadOwnerDeliveryRouter` with real
``AsyncSession`` and mocked Telegram HTTP.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.integrations.telegram.lead_alert_types import TelegramSendTarget
from app.models.bot import Bot
from app.models.enums import UserRole
from app.models.lead import Lead
from app.models.lead_event import LeadEvent
from app.models.user import User
from app.services.lead_owner_delivery_router import LeadOwnerDeliveryRouter
from app.services.telegram_lead_alert_service import TelegramLeadAlertService
from sqlalchemy import select

from tests.integration_db import integration_database_url

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
def _alembic_for_lead_delivery() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def _unique_email(prefix: str = "deliver") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


class _FixedTokProvider:
    def __init__(self, target: TelegramSendTarget) -> None:
        self._t = target

    async def resolve_target(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> TelegramSendTarget | None:
        return self._t


@pytest.mark.asyncio
async def test_router_stamps_inbox_telegram_delivered_and_timeline_events(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    try:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["json"] = json.loads(request.content.decode())
            return httpx.Response(200, json={"ok": True})

        transport = httpx.MockTransport(handler)
        target = TelegramSendTarget(bot_token="MOCK_TOK", chat_id="112233")

        sm = get_session_maker()
        async with sm() as session:
            owner = User(
                email=_unique_email("ok-owner"),
                password_hash="bcrypt$dummy",
                role=UserRole.customer_admin,
            )
            session.add(owner)
            await session.flush()
            bot = Bot(
                owner_id=owner.id,
                name="Delivery Bot",
                niche_id="education",
                goal_type="sales",
                status="active",
            )
            session.add(bot)
            await session.flush()
            lead = Lead(
                bot_id=bot.id,
                owner_id=owner.id,
                niche_id="education",
                lead_temperature="warm",
                phone="+15550001111",
            )
            session.add(lead)
            await session.commit()
            await session.refresh(lead)
            await session.refresh(owner)

            async with httpx.AsyncClient(transport=transport) as client:
                tg = TelegramLeadAlertService(_FixedTokProvider(target), http_client=client)
                router = LeadOwnerDeliveryRouter(telegram_alerts=tg)
                await router.route_new_lead_after_commit(
                    session,
                    owner_id=owner.id,
                    owner_user=owner,
                    bot=bot,
                    lead=lead,
                )

        assert "sendMessage" in str(captured.get("url", ""))
        assert captured["json"]["chat_id"] == "112233"

        async with sm() as session:
            row = (
                await session.execute(select(Lead).where(Lead.id == lead.id).limit(1))
            ).scalar_one()
            assert row.owner_inbox_routed_at is not None
            assert row.telegram_delivery_status == "delivered"
            assert row.telegram_delivery_attempts >= 1
            assert row.telegram_delivery_updated_at is not None

            evs = list(
                (
                    await session.execute(
                        select(LeadEvent).where(LeadEvent.lead_id == lead.id).order_by(LeadEvent.created_at),
                    )
                ).scalars().all()
            )
            kinds = [e.event_type for e in evs]
            assert "system_action" in kinds
            assert "notification_delivered" in kinds
    finally:
        await dispose_engine()
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_router_telegram_failure_records_failed_status_and_timeline(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    try:

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={})

        transport = httpx.MockTransport(handler)
        target = TelegramSendTarget(bot_token="MOCK_TOK", chat_id="445566")

        sm = get_session_maker()
        async with sm() as session:
            owner = User(
                email=_unique_email("fail-owner"),
                password_hash="bcrypt$dummy",
                role=UserRole.customer_admin,
            )
            session.add(owner)
            await session.flush()
            bot = Bot(
                owner_id=owner.id,
                name="Fail Bot",
                niche_id="education",
                goal_type="sales",
                status="active",
            )
            session.add(bot)
            await session.flush()
            lead = Lead(bot_id=bot.id, owner_id=owner.id, niche_id="education")
            session.add(lead)
            await session.commit()
            await session.refresh(lead)
            await session.refresh(owner)

            async with httpx.AsyncClient(transport=transport) as client:
                tg = TelegramLeadAlertService(_FixedTokProvider(target), http_client=client)
                router = LeadOwnerDeliveryRouter(telegram_alerts=tg)
                await router.route_new_lead_after_commit(
                    session,
                    owner_id=owner.id,
                    owner_user=owner,
                    bot=bot,
                    lead=lead,
                )

        async with sm() as session:
            row = (
                await session.execute(select(Lead).where(Lead.id == lead.id).limit(1))
            ).scalar_one()
            assert row.telegram_delivery_status == "failed"
            evs = [
                e.event_type
                for e in (
                    await session.execute(select(LeadEvent).where(LeadEvent.lead_id == lead.id))
                ).scalars().all()
            ]
            assert "notification_failed" in evs
    finally:
        await dispose_engine()
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_router_skips_telegram_when_owner_disables_pref(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    try:
        sm = get_session_maker()
        async with sm() as session:
            owner = User(
                email=_unique_email("pref-off"),
                password_hash="bcrypt$dummy",
                role=UserRole.customer_admin,
                lead_telegram_alerts_enabled=False,
            )
            session.add(owner)
            await session.flush()
            bot = Bot(
                owner_id=owner.id,
                name="Pref Bot",
                niche_id="education",
                goal_type="sales",
                status="active",
            )
            session.add(bot)
            await session.flush()
            lead = Lead(bot_id=bot.id, owner_id=owner.id, niche_id="education")
            session.add(lead)
            await session.commit()
            await session.refresh(lead)
            await session.refresh(owner)

            target = TelegramSendTarget(bot_token="SHOULD_NOT_USE", chat_id="999")
            tg = TelegramLeadAlertService(_FixedTokProvider(target))
            router = LeadOwnerDeliveryRouter(telegram_alerts=tg)
            await router.route_new_lead_after_commit(
                session,
                owner_id=owner.id,
                owner_user=owner,
                bot=bot,
                lead=lead,
            )

        async with sm() as session:
            row = (
                await session.execute(select(Lead).where(Lead.id == lead.id).limit(1))
            ).scalar_one()
            assert row.owner_inbox_routed_at is not None
            assert row.telegram_delivery_status == "skipped_owner_pref"
            assert row.telegram_delivery_attempts == 0
    finally:
        await dispose_engine()
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_lead_row_always_exists_for_owner_list_no_silent_loss(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lead persists even when delivery router is None (capture never depends on outbound notify)."""
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    try:
        sm = get_session_maker()
        async with sm() as session:
            owner = User(
                email=_unique_email("silent"),
                password_hash="bcrypt$dummy",
                role=UserRole.customer_admin,
            )
            session.add(owner)
            await session.flush()
            bot = Bot(
                owner_id=owner.id,
                name="Silent Bot",
                niche_id="education",
                goal_type="sales",
                status="active",
            )
            session.add(bot)
            await session.flush()
            lead = Lead(bot_id=bot.id, owner_id=owner.id, niche_id="education")
            session.add(lead)
            await session.commit()
            oid, lid = owner.id, lead.id

        async with sm() as session:
            n = (
                await session.execute(select(Lead).where(Lead.owner_id == oid, Lead.id == lid))
            ).scalar_one_or_none()
            assert n is not None
            assert n.owner_id == oid
    finally:
        await dispose_engine()
        get_settings.cache_clear()
