"""
Route a **newly committed** CRM lead to owner surfaces: dashboard inbox, Telegram, future channels.

Call **only after** the transaction that inserted the lead has committed. Updates delivery columns,
writes append-only :class:`~app.models.lead_event.LeadEvent` rows, and commits ``session`` once.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.repositories.lead_event_repository import LeadEventRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.email_service import EmailService
from app.services.lead_event_service import LeadEventService
from app.services.owner_notification_service import OwnerNotificationService
from app.services.telegram_lead_alert_service import TelegramLeadAlertService

if TYPE_CHECKING:
    from app.models.bot import Bot
    from app.models.lead import Lead
    from app.models.user import User

_LOG = get_logger("lead_owner_delivery")


class LeadOwnerDeliveryRouter:
    """
    Single entry point for new-lead owner delivery after persistence succeeds.

    **Dashboard notification:** Creates an :class:`~app.models.owner_notification.OwnerNotification`
    row so the bell icon shows new leads instantly.

    **Dashboard inbox:** Leads are already owner-scoped rows; we stamp ``owner_inbox_routed_at`` and emit
    a ``system_action`` so support can prove the inbox path ran (no silent DB-only capture).

    **Telegram:** Uses :class:`~app.services.telegram_lead_alert_service.TelegramLeadAlertService`
    (retries inside the HTTP client). Skips when the owner disables Telegram alerts or no target
    exists.

    **Email / webhooks:** Placeholder event when ``lead_email_alerts_enabled`` is true — extensible
    without changing the capture transaction.
    """

    def __init__(
        self,
        telegram_alerts: TelegramLeadAlertService | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        self._telegram = telegram_alerts
        self._email = email_service

    async def route_new_lead_after_commit(
        self,
        session: AsyncSession,
        *,
        owner_id: uuid.UUID,
        owner_user: "User | None",
        bot: "Bot",
        lead: "Lead",
    ) -> None:
        if getattr(lead, "owner_inbox_routed_at", None) is not None:
            return

        now = datetime.now(tz=UTC)
        events = LeadEventService(LeadEventRepository(session))

        try:
            lead.owner_inbox_routed_at = now
            await events.emit_system_action(
                lead_id=lead.id,
                action="owner_dashboard_inbox",
                metadata={
                    "surface": "crm_leads_api",
                    "owner_id": str(owner_id),
                    "message": "Lead row is owner-scoped and listed via GET /api/v1/leads.",
                },
            )

            # Dashboard bell notification
            try:
                notif_svc = OwnerNotificationService(NotificationRepository(session))
                await notif_svc.notify_new_lead(
                    owner_id=owner_id,
                    bot=bot,
                    lead=lead,
                )
            except Exception:
                _LOG.warning(
                    "lead_dashboard_notification_failed",
                    exc_info=True,
                    lead_id=str(lead.id),
                    owner_id=str(owner_id),
                )

            tg_enabled = True
            if owner_user is not None:
                tg_enabled = bool(getattr(owner_user, "lead_telegram_alerts_enabled", True))

            if not tg_enabled:
                lead.telegram_delivery_status = "skipped_owner_pref"
                lead.telegram_delivery_attempts = 0
                lead.telegram_delivery_updated_at = now
                await events.emit_system_action(
                    lead_id=lead.id,
                    action="lead_delivery_telegram",
                    metadata={"outcome": "skipped", "reason": "owner_disabled"},
                )
            elif self._telegram is None:
                lead.telegram_delivery_status = "skipped_not_configured"
                lead.telegram_delivery_attempts = 0
                lead.telegram_delivery_updated_at = now
                await events.emit_system_action(
                    lead_id=lead.id,
                    action="lead_delivery_telegram",
                    metadata={"outcome": "skipped", "reason": "service_not_wired"},
                )
            else:
                tg = await self._telegram.attempt_send_new_lead_alert(
                    owner_id=owner_id,
                    bot=bot,
                    lead=lead,
                )
                lead.telegram_delivery_attempts = tg.attempts
                lead.telegram_delivery_updated_at = now
                if tg.outcome == "skipped_no_target":
                    lead.telegram_delivery_status = "skipped_no_target"
                    await events.emit_system_action(
                        lead_id=lead.id,
                        action="lead_delivery_telegram",
                        metadata={"outcome": "skipped", "reason": "no_target"},
                    )
                elif tg.outcome == "delivered":
                    lead.telegram_delivery_status = "delivered"
                    await events.emit_notification_outcome(
                        lead_id=lead.id,
                        channel="telegram",
                        ok=True,
                        metadata={
                            "attempts": tg.attempts,
                            "last_status_code": tg.last_status_code,
                            "error_kind": tg.error_kind,
                        },
                    )
                else:
                    lead.telegram_delivery_status = "failed"
                    await events.emit_notification_outcome(
                        lead_id=lead.id,
                        channel="telegram",
                        ok=False,
                        metadata={
                            "attempts": tg.attempts,
                            "last_status_code": tg.last_status_code,
                            "error_kind": tg.error_kind,
                        },
                    )

            email_on = False
            if owner_user is not None:
                email_on = bool(getattr(owner_user, "lead_email_alerts_enabled", False))
            if email_on:
                if self._email is None:
                    await events.emit_system_action(
                        lead_id=lead.id,
                        action="lead_delivery_email",
                        metadata={"outcome": "skipped", "reason": "service_not_wired"},
                    )
                else:
                    try:
                        ok = await self._email.send_lead_alert_email(
                            to_email=owner_user.email,
                            owner_name=owner_user.full_name,
                            lead_name=lead.name,
                            lead_phone=lead.phone,
                            lead_status=lead.status,
                            lead_temperature=lead.lead_temperature,
                            bot_name=bot.name,
                            summary=lead.summary,
                        )
                        await events.emit_notification_outcome(
                            lead_id=lead.id,
                            channel="email",
                            ok=ok,
                            metadata={"outcome": "delivered" if ok else "failed"},
                        )
                    except Exception:
                        _LOG.exception(
                            "lead_email_alert_failed",
                            lead_id=str(lead.id),
                            owner_id=str(owner_id),
                        )
                        await events.emit_system_action(
                            lead_id=lead.id,
                            action="lead_delivery_email",
                            metadata={"outcome": "error", "reason": "exception"},
                        )

            await session.commit()
        except Exception:
            _LOG.exception(
                "lead_owner_delivery_failed",
                lead_id=str(lead.id),
                owner_id=str(owner_id),
            )
            try:
                await session.rollback()
            except Exception:
                _LOG.exception("lead_owner_delivery_rollback_failed", lead_id=str(lead.id))


__all__ = ["LeadOwnerDeliveryRouter"]
