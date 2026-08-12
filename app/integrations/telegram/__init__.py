"""
Telegram outbound integration (new-lead alerts).

Integration hook (callers)
==========================

1. **After the DB transaction that creates the lead has committed**, run
   :meth:`app.services.lead_owner_delivery_router.LeadOwnerDeliveryRouter.route_new_lead_after_commit`
   (or call :meth:`app.services.telegram_lead_alert_service.TelegramLeadAlertService.attempt_send_new_lead_alert`
   from a custom router). Do **not** send inside the same unit of work as ``create_lead`` — outbound
   latency and failures must not roll back persistence.

2. Wire a :class:`~app.integrations.telegram.lead_alert_target.LeadTelegramAlertTargetProvider`.
   For local MVP use :class:`~app.integrations.telegram.lead_alert_target.EnvLeadTelegramAlertTargetProvider`
   (global token + chat from settings). Swap for a DB resolver when ``users`` / ``bots`` store
   per-owner chat ids without changing the alert service.

3. **Secrets:** never log bot tokens or chat ids. Outcomes are logged with ``lead_id`` and coarse
   error kinds only.

Modules
=======

* ``lead_alert_types`` — payload + send target dataclasses
* ``lead_alert_message`` — :func:`lead_alert_message.format_new_lead_alert_message`
* ``telegram_send`` — :func:`telegram_send.send_telegram_text_message` (retries)
* ``lead_alert_target`` — provider protocol + env MVP implementation
"""

from app.integrations.telegram.lead_alert_message import format_new_lead_alert_message
from app.integrations.telegram.lead_alert_target import (
    EnvLeadTelegramAlertTargetProvider,
    LeadTelegramAlertTargetProvider,
)
from app.integrations.telegram.lead_alert_types import NewLeadAlertPayload, TelegramSendTarget
from app.integrations.telegram.telegram_send import TelegramSendOutcome, send_telegram_text_message

__all__ = [
    "EnvLeadTelegramAlertTargetProvider",
    "LeadTelegramAlertTargetProvider",
    "NewLeadAlertPayload",
    "TelegramSendOutcome",
    "TelegramSendTarget",
    "format_new_lead_alert_message",
    "send_telegram_text_message",
]
