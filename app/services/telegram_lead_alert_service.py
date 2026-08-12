"""
Facade for new-lead Telegram alerts (transport only).

Orchestration, owner preferences, CRM events, and delivery columns are handled by
:class:`~app.services.lead_owner_delivery_router.LeadOwnerDeliveryRouter`.

HTTP, retries, and formatting live under ``app.integrations.telegram``.
This service never raises to callers — failures are logged without token/chat leakage.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import httpx

from app.contracts.lead_owner_delivery import TelegramChannelAttemptResult
from app.core.logging import get_logger
from app.integrations.telegram.lead_alert_message import format_new_lead_alert_message
from app.integrations.telegram.lead_alert_target import LeadTelegramAlertTargetProvider
from app.integrations.telegram.lead_alert_types import NewLeadAlertPayload
from app.integrations.telegram.telegram_send import send_telegram_text_message

if TYPE_CHECKING:
    from app.models.bot import Bot
    from app.models.lead import Lead

_LOG = get_logger("telegram_lead_alert")


def new_lead_alert_payload(*, bot_name: str, lead: "Lead") -> NewLeadAlertPayload:
    """Map ORM row + bot display name to a formatting snapshot."""
    return NewLeadAlertPayload(
        lead_id=lead.id,
        bot_name=(bot_name or "").strip() or "(unnamed bot)",
        niche_id=(lead.niche_id or "").strip() or "—",
        lead_temperature=lead.lead_temperature,
        phone=lead.phone,
        summary=lead.summary,
        lead_score=lead.lead_score,
        captured_at=lead.created_at,
        source_channel=(lead.source_channel or "").strip() or None,
    )


class TelegramLeadAlertService:
    """
    Send optional Telegram notifications for new leads.

    Inject a :class:`~app.integrations.telegram.lead_alert_target.LeadTelegramAlertTargetProvider`.
    When it returns ``None``, :meth:`attempt_send_new_lead_alert` reports ``skipped_no_target``.
    """

    def __init__(
        self,
        target_provider: LeadTelegramAlertTargetProvider,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._targets = target_provider
        self._http_client = http_client

    async def attempt_send_new_lead_alert(
        self,
        *,
        owner_id: uuid.UUID,
        bot: "Bot",
        lead: "Lead",
    ) -> TelegramChannelAttemptResult:
        """
        Perform sendMessage with bounded retries (see :mod:`app.integrations.telegram.telegram_send`).

        Never raises. Does **not** write to the database.
        """
        try:
            target = await self._targets.resolve_target(owner_id=owner_id, bot_id=bot.id)
            if target is None:
                return TelegramChannelAttemptResult(outcome="skipped_no_target")
            payload = new_lead_alert_payload(bot_name=bot.name, lead=lead)
            text = format_new_lead_alert_message(payload)
            outcome = await send_telegram_text_message(
                target,
                text,
                client=self._http_client,
            )
            if outcome.ok:
                _LOG.info(
                    "telegram_lead_alert_sent",
                    lead_id=str(lead.id),
                    attempts=outcome.attempts,
                )
                return TelegramChannelAttemptResult(
                    outcome="delivered",
                    attempts=outcome.attempts,
                    last_status_code=outcome.last_status_code,
                    error_kind=outcome.error_kind,
                )
            _LOG.warning(
                "telegram_lead_alert_failed",
                lead_id=str(lead.id),
                attempts=outcome.attempts,
                last_status_code=outcome.last_status_code,
                error_kind=outcome.error_kind,
            )
            return TelegramChannelAttemptResult(
                outcome="failed",
                attempts=outcome.attempts,
                last_status_code=outcome.last_status_code,
                error_kind=outcome.error_kind,
            )
        except Exception:
            _LOG.exception(
                "telegram_lead_alert_unexpected_error",
                lead_id=str(lead.id),
            )
            return TelegramChannelAttemptResult(
                outcome="failed",
                attempts=0,
                last_status_code=None,
                error_kind="unexpected_exception",
            )

    async def notify_new_lead_safe(
        self,
        *,
        owner_id: uuid.UUID,
        bot: "Bot",
        lead: "Lead",
    ) -> None:
        """
        Log-only helper for legacy call sites and unit tests (no DB side effects).

        Prefer :class:`~app.services.lead_owner_delivery_router.LeadOwnerDeliveryRouter` in production.
        """
        await self.attempt_send_new_lead_alert(owner_id=owner_id, bot=bot, lead=lead)


__all__ = ["TelegramLeadAlertService", "new_lead_alert_payload"]
