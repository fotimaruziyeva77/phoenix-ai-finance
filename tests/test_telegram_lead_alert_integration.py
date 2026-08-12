"""
Integration-style tests: lead creation → Telegram alert (mocked HTTP).

``LeadCreationService`` stays free of Telegram imports; this module documents the post-commit hook.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
from app.integrations.telegram.lead_alert_types import TelegramSendTarget
from app.services.lead_creation_service import LeadCreationService
from app.services.telegram_lead_alert_service import TelegramLeadAlertService


def _owner(oid: uuid.UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=oid or uuid.uuid4())


def _bot(*, owner_id: uuid.UUID, bid: uuid.UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=bid or uuid.uuid4(),
        owner_id=owner_id,
        goal_type="sales",
        niche_id="generic",
        name="Widget Sales Bot",
    )


def _conversation(*, owner_id: uuid.UUID, bot_id: uuid.UUID) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        owner_id=owner_id,
        bot_id=bot_id,
        current_state="closing",
        niche_id_snapshot="generic",
    )


class _LeadRepoWithCreatedAt:
    """Stub repo: returned lead includes ``created_at`` (required by alert payload)."""

    def __init__(self) -> None:
        self.create_calls: list[dict[str, object]] = []

    async def get_lead_by_conversation_id(self, conversation_id: uuid.UUID) -> None:
        return None

    async def find_open_lead_same_normalized_phone(self, **kwargs: object) -> None:
        return None

    async def count_leads_same_phone_recent(self, **kwargs: object) -> int:
        return 0

    async def create_lead(self, **kwargs: object) -> SimpleNamespace:
        self.create_calls.append(dict(kwargs))
        fixed_ts = datetime(2026, 4, 3, 15, 45, tzinfo=timezone.utc)
        return SimpleNamespace(
            id=uuid.uuid4(),
            created_at=fixed_ts,
            **kwargs,
        )


class _FixedTargetProvider:
    def __init__(self, target: TelegramSendTarget) -> None:
        self._target = target

    async def resolve_target(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> TelegramSendTarget | None:
        return self._target


def test_lead_creation_service_has_no_telegram_dependency() -> None:
    """Orchestration stays mockable: constructor takes the lead repository (+ optional timeline)."""
    sig = inspect.signature(LeadCreationService.__init__)
    params = list(sig.parameters.keys())
    assert params[:2] == ["self", "lead_repo"]
    assert "events" in params
    mod = importlib.import_module("app.services.lead_creation_service")
    assert not hasattr(mod, "TelegramLeadAlertService")
    assert not hasattr(mod, "notify_new_lead")


def test_message_format_expected_sections() -> None:
    """Alert text uses stable section labels for parsing and human scan."""
    from app.integrations.telegram.lead_alert_message import format_new_lead_alert_message
    from app.integrations.telegram.lead_alert_types import NewLeadAlertPayload

    p = NewLeadAlertPayload(
        lead_id=uuid.uuid4(),
        bot_name="B",
        niche_id="n",
        lead_temperature="hot",
        phone="+1",
        summary="Line one.\nLine two.",
        lead_score=42,
        captured_at=datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc),
    )
    text = format_new_lead_alert_message(p)
    assert text.startswith("New lead — BotForge AI\n")
    assert "\nBot: B\n" in text
    assert "\nNiche: n\n" in text
    assert "\nSource: —\n" in text
    assert "\nTemperature: hot\n" in text
    assert "\nScore: 42\n" in text
    assert "\nPhone: +1\n" in text
    assert "\nSummary:\n" in text
    assert "Line one.\nLine two." in text


def test_lead_creation_then_mocked_telegram_receives_formatted_body() -> None:
    """After a successful create, post-commit alert sends JSON with expected message text."""
    owner_id = uuid.uuid4()
    bot = _bot(owner_id=owner_id)
    conv = _conversation(owner_id=owner_id, bot_id=bot.id)
    owner = _owner(owner_id)
    repo = _LeadRepoWithCreatedAt()
    creation = LeadCreationService(repo)

    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    target = TelegramSendTarget(bot_token="MOCK_TOKEN", chat_id="999888")
    created_lead_id: uuid.UUID | None = None

    async def run() -> None:
        nonlocal created_lead_id
        res = await creation.try_create_lead_from_conversation(
            bot=bot,
            owner=owner,
            conversation=conv,
            collected_data_json={"primary_need": "widgets", "phone": "+15550001111"},
            lead_score=81,
            lead_temperature="hot",
            summary="Ready to buy enterprise plan.",
            source_channel="web_chat",
        )
        assert res.created is True
        assert res.lead is not None
        created_lead_id = res.lead.id
        async with httpx.AsyncClient(transport=transport) as client:
            alert = TelegramLeadAlertService(_FixedTargetProvider(target), http_client=client)
            await alert.notify_new_lead_safe(owner_id=owner_id, bot=bot, lead=res.lead)

    asyncio.run(run())

    assert created_lead_id is not None
    assert "sendMessage" in str(captured.get("url", ""))
    body = captured["json"]
    assert isinstance(body, dict)
    assert body.get("chat_id") == "999888"
    assert body.get("disable_web_page_preview") is True
    msg = body.get("text", "")
    assert isinstance(msg, str)
    assert "Widget Sales Bot" in msg
    assert "generic" in msg
    assert "hot" in msg
    assert "81" in msg
    assert "+15550001111" in msg
    assert "Ready to buy enterprise plan." in msg
    assert str(created_lead_id) in msg
    assert "Lead ID:" in msg


def test_telegram_failure_does_not_mutate_lead_snapshot() -> None:
    """Simulated post-commit alert failure leaves the persisted lead fields intact."""
    owner_id = uuid.uuid4()
    bot = _bot(owner_id=owner_id)
    conv = _conversation(owner_id=owner_id, bot_id=bot.id)
    owner = _owner(owner_id)
    repo = _LeadRepoWithCreatedAt()
    creation = LeadCreationService(repo)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={})

    transport = httpx.MockTransport(handler)
    target = TelegramSendTarget(bot_token="tok", chat_id="1")

    async def run() -> None:
        res = await creation.try_create_lead_from_conversation(
            bot=bot,
            owner=owner,
            conversation=conv,
            collected_data_json={"primary_need": "x", "phone": "+1"},
            lead_score=55,
            lead_temperature="warm",
            summary="Keep me",
            source_channel="web_chat",
        )
        assert res.created and res.lead is not None
        lead = res.lead
        before = (
            lead.id,
            lead.summary,
            lead.phone,
            lead.lead_score,
            lead.lead_temperature,
            lead.niche_id,
        )
        async with httpx.AsyncClient(transport=transport) as client:
            alert = TelegramLeadAlertService(_FixedTargetProvider(target), http_client=client)
            await alert.notify_new_lead_safe(owner_id=owner_id, bot=bot, lead=lead)
        after = (
            lead.id,
            lead.summary,
            lead.phone,
            lead.lead_score,
            lead.lead_temperature,
            lead.niche_id,
        )
        assert before == after

    asyncio.run(run())


def test_telegram_provider_exception_does_not_mutate_lead() -> None:
    owner_id = uuid.uuid4()
    bot = _bot(owner_id=owner_id)
    lead = SimpleNamespace(
        id=uuid.uuid4(),
        niche_id="n",
        lead_temperature="cold",
        phone="+1",
        summary="S",
        lead_score=1,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    provider = MagicMock()
    provider.resolve_target = AsyncMock(side_effect=RuntimeError("resolver down"))
    svc = TelegramLeadAlertService(provider)

    async def run() -> None:
        snap = (lead.summary, lead.phone)
        await svc.notify_new_lead_safe(owner_id=owner_id, bot=bot, lead=lead)
        assert (lead.summary, lead.phone) == snap

    asyncio.run(run())


def test_telegram_alert_service_is_replaceable_with_async_mock() -> None:
    """Callers can inject a stand-in for the whole service (no httpx, no provider)."""
    mock_svc = AsyncMock(spec=TelegramLeadAlertService)
    owner_id = uuid.uuid4()
    bot = _bot(owner_id=owner_id)
    lead = SimpleNamespace(
        id=uuid.uuid4(),
        niche_id="x",
        lead_temperature=None,
        phone=None,
        summary=None,
        lead_score=None,
        created_at=datetime.now(tz=timezone.utc),
    )

    async def run() -> None:
        await mock_svc.notify_new_lead_safe(owner_id=owner_id, bot=bot, lead=lead)

    asyncio.run(run())
    mock_svc.notify_new_lead_safe.assert_awaited_once()
    call_kw = mock_svc.notify_new_lead_safe.await_args.kwargs
    assert call_kw["owner_id"] == owner_id
    assert call_kw["lead"] is lead
