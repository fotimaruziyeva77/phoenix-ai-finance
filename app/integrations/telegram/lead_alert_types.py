"""Plain data for new-lead Telegram alerts (no ORM imports)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class NewLeadAlertPayload:
    """Snapshot used only for formatting and outbound delivery."""

    lead_id: uuid.UUID
    bot_name: str
    niche_id: str
    lead_temperature: str | None
    phone: str | None
    summary: str | None
    lead_score: int | None
    captured_at: datetime
    source_channel: str | None = None


@dataclass(frozen=True, slots=True)
class TelegramSendTarget:
    """Where to send a single message (replace with per-owner/bot DB config later)."""

    bot_token: str
    chat_id: str
