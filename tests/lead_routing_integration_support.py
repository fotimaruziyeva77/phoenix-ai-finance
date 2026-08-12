"""
Shared helpers for lead routing integration tests (CRM capture, owner delivery, Telegram HTTP edge).

* **Inner loop:** real :class:`~app.services.sales_conversation_orchestrator.SalesConversationOrchestrator`,
  :class:`~app.repositories.lead_repository.LeadRepository`, and
  :class:`~app.services.lead_owner_delivery_router.LeadOwnerDeliveryRouter`.
* **Outer boundary:** ``httpx.MockTransport`` stands in for Telegram ``sendMessage`` (no network).

**Observability (assert on ``Lead`` + ``lead_events``)**

* ``owner_inbox_routed_at`` — proves the post-commit delivery router ran the inbox path.
* ``telegram_delivery_status`` / ``telegram_delivery_attempts`` / ``telegram_delivery_updated_at`` —
  persisted notify outcome on the CRM row.
* Timeline: ``lead_created``, ``system_action``, ``notification_delivered`` or ``notification_failed``.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
from alembic import command
from alembic.config import Config
from app.core.config import Settings, get_settings
from app.integrations.telegram.lead_alert_types import TelegramSendTarget
from app.services.lead_owner_delivery_router import LeadOwnerDeliveryRouter
from app.services.sales_conversation_orchestrator import SalesConversationOrchestrator
from app.services.telegram_lead_alert_service import TelegramLeadAlertService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def alembic_upgrade_head(database_url: str) -> None:
    import os

    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
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


class FixedTelegramSendTargetProvider:
    """Always return the same send target (avoids DB TelegramConfig setup in routing tests)."""

    def __init__(self, target: TelegramSendTarget) -> None:
        self._t = target

    async def resolve_target(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> TelegramSendTarget | None:
        return self._t


def mock_telegram_send_message_transport(*, status_code: int = 200, ok: bool = True) -> httpx.MockTransport:
    """Simulate Telegram Bot API ``sendMessage`` responses."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert "sendMessage" in str(request.url)
        _ = json.loads(request.content.decode())
        body: dict[str, Any] = {"ok": ok}
        if ok:
            body["result"] = {"message_id": 1}
        return httpx.Response(status_code, json=body)

    return httpx.MockTransport(handler)


async def make_orchestrator_with_delivery(
    *,
    chat_repo: Any,
    bot_repo: Any,
    settings: Settings,
    intent_classifier: Any,
    provider_resolver: Callable[[Settings, str | None], Any],
    http_client: httpx.AsyncClient,
    telegram_target: TelegramSendTarget,
) -> SalesConversationOrchestrator:
    tg = TelegramLeadAlertService(
        FixedTelegramSendTargetProvider(telegram_target),
        http_client=http_client,
    )
    router = LeadOwnerDeliveryRouter(telegram_alerts=tg)
    return SalesConversationOrchestrator(
        chat_repo,
        bot_repo,
        settings=settings,
        intent_classifier=intent_classifier,
        provider_resolver=provider_resolver,
        lead_owner_delivery=router,
    )


async def fetch_lead_event_types(session: AsyncSession, lead_id: uuid.UUID) -> list[str]:
    from app.models.lead_event import LeadEvent

    rows = (
        await session.execute(select(LeadEvent.event_type).where(LeadEvent.lead_id == lead_id).order_by(LeadEvent.created_at))
    ).all()
    return [str(r[0]) for r in rows]


__all__ = [
    "PROJECT_ROOT",
    "FixedTelegramSendTargetProvider",
    "alembic_upgrade_head",
    "fetch_lead_event_types",
    "make_orchestrator_with_delivery",
    "mock_telegram_send_message_transport",
]
