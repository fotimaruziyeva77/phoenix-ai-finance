"""
Shared types for routing a **new CRM lead** to owner-facing surfaces after DB commit.

Channel adapters (Telegram, future email/webhook) return structured outcomes consumed by
:class:`~app.services.lead_owner_delivery_router.LeadOwnerDeliveryRouter`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal


TelegramAttemptOutcome = Literal["skipped_no_target", "delivered", "failed"]


@dataclass(frozen=True, slots=True)
class NewLeadDeliveryContext:
    """Immutable routing identifiers (after the lead row exists and is committed)."""

    owner_id: uuid.UUID
    bot_id: uuid.UUID
    lead_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class TelegramChannelAttemptResult:
    """Telegram Bot API send outcome (safe to log; no secrets)."""

    outcome: TelegramAttemptOutcome
    attempts: int = 0
    last_status_code: int | None = None
    error_kind: str | None = None


__all__ = [
    "NewLeadDeliveryContext",
    "TelegramAttemptOutcome",
    "TelegramChannelAttemptResult",
]
