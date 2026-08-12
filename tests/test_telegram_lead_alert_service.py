"""Tests for :mod:`app.services.telegram_lead_alert_service`."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
from app.integrations.telegram.lead_alert_types import TelegramSendTarget
from app.services.telegram_lead_alert_service import TelegramLeadAlertService, new_lead_alert_payload


class _FixedTargetProvider:
    def __init__(self, target: TelegramSendTarget | None) -> None:
        self._target = target

    async def resolve_target(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> TelegramSendTarget | None:
        return self._target


def _bot(*, bid: uuid.UUID | None = None, name: str = "Bot") -> SimpleNamespace:
    return SimpleNamespace(id=bid or uuid.uuid4(), name=name)


def _lead(
    *,
    lid: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    source_channel: str | None = None,
) -> SimpleNamespace:
    oid = owner_id or uuid.uuid4()
    return SimpleNamespace(
        id=lid or uuid.uuid4(),
        owner_id=oid,
        niche_id="services",
        lead_temperature="warm",
        phone="+1999",
        summary="Need HVAC",
        lead_score=50,
        created_at=datetime(2026, 4, 3, 10, 0, tzinfo=timezone.utc),
        source_channel=source_channel,
    )


def test_new_lead_alert_payload_maps_fields() -> None:
    bot = _bot(name=" AC Co ")
    lead = _lead(source_channel="telegram")
    p = new_lead_alert_payload(bot_name=bot.name, lead=lead)
    assert p.bot_name == "AC Co"
    assert p.niche_id == "services"
    assert p.phone == "+1999"
    assert p.summary == "Need HVAC"
    assert p.lead_score == 50
    assert p.source_channel == "telegram"


def test_new_lead_alert_payload_source_channel_omitted_when_empty() -> None:
    bot = _bot()
    lead = _lead(source_channel=None)
    p = new_lead_alert_payload(bot_name=bot.name, lead=lead)
    assert p.source_channel is None


def test_notify_skips_when_no_target() -> None:
    owner_id = uuid.uuid4()
    bot = _bot()
    lead = _lead(owner_id=owner_id)
    svc = TelegramLeadAlertService(_FixedTargetProvider(None))

    async def run() -> None:
        await svc.notify_new_lead_safe(owner_id=owner_id, bot=bot, lead=lead)

    asyncio.run(run())


def test_attempt_send_returns_skipped_no_target_without_http() -> None:
    owner_id = uuid.uuid4()
    bot = _bot()
    lead = _lead(owner_id=owner_id)
    svc = TelegramLeadAlertService(_FixedTargetProvider(None))

    async def run() -> None:
        r = await svc.attempt_send_new_lead_alert(owner_id=owner_id, bot=bot, lead=lead)
        assert r.outcome == "skipped_no_target"
        assert r.attempts == 0

    asyncio.run(run())


def test_notify_does_not_raise_on_send_failure() -> None:
    owner_id = uuid.uuid4()
    bot = _bot()
    lead = _lead(owner_id=owner_id)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={})

    transport = httpx.MockTransport(handler)
    target = TelegramSendTarget(bot_token="tok", chat_id="1")

    async def run() -> None:
        async with httpx.AsyncClient(transport=transport) as client:
            svc = TelegramLeadAlertService(_FixedTargetProvider(target), http_client=client)
            await svc.notify_new_lead_safe(owner_id=owner_id, bot=bot, lead=lead)

    asyncio.run(run())


def test_notify_swallows_malformed_json_response() -> None:
    """Telegram edge cases must not propagate past ``notify_new_lead_safe``."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    transport = httpx.MockTransport(handler)
    target = TelegramSendTarget(bot_token="tok", chat_id="1")
    owner_id = uuid.uuid4()
    bot = _bot()
    lead = _lead(owner_id=owner_id)

    async def run() -> None:
        async with httpx.AsyncClient(transport=transport) as client:
            svc = TelegramLeadAlertService(_FixedTargetProvider(target), http_client=client)
            await svc.notify_new_lead_safe(owner_id=owner_id, bot=bot, lead=lead)

    asyncio.run(run())


def test_notify_succeeds_on_ok_response() -> None:
    owner_id = uuid.uuid4()
    bot = _bot()
    lead = _lead(owner_id=owner_id)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    target = TelegramSendTarget(bot_token="tok", chat_id="1")

    async def run() -> None:
        async with httpx.AsyncClient(transport=transport) as client:
            svc = TelegramLeadAlertService(_FixedTargetProvider(target), http_client=client)
            await svc.notify_new_lead_safe(owner_id=owner_id, bot=bot, lead=lead)

    asyncio.run(run())
