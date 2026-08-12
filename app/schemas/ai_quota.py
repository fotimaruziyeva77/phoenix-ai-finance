"""AI usage quota read models (dashboard + operator visibility)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AIQuotaWindowRead(BaseModel):
    """One enforcement window (totals from ``ai_usage_logs.tokens_total``)."""

    enforced: bool = Field(description="False when cap is 0 (local/dev unlimited).")
    used_tokens: int = Field(ge=0)
    cap_tokens: int | None = Field(
        default=None,
        ge=0,
        description="Maximum tokens for this window; null when not enforced.",
    )
    measure: Literal["tokens_total"] = "tokens_total"
    resets_at_utc: datetime | None = Field(
        default=None,
        description="UTC instant when this counter resets (start of next day or month).",
    )


class AIUsageQuotaRead(BaseModel):
    """Current usage vs configured caps for one bot and its owner."""

    bot_id: UUID
    owner_id: UUID
    bot_daily: AIQuotaWindowRead
    owner_monthly: AIQuotaWindowRead
