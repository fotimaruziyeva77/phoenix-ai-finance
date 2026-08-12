"""Support ticket request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject:  str = Field(..., min_length=3, max_length=256)
    body:     str = Field(..., min_length=10, max_length=8000)
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")


class TicketRead(BaseModel):
    id:          UUID
    user_id:     UUID
    subject:     str
    body:        str
    status:      str
    priority:    str
    admin_note:  str | None = None
    resolved_at: datetime | None = None
    created_at:  datetime
    updated_at:  datetime


class TicketListResponse(BaseModel):
    items: list[TicketRead]
    total: int = Field(ge=0)
    limit: int
    offset: int


# ── Admin ─────────────────────────────────────────────────────────────────

class AdminTicketRead(TicketRead):
    user_email: str


class AdminTicketListResponse(BaseModel):
    items: list[AdminTicketRead]
    total: int = Field(ge=0)
    limit: int
    offset: int


class AdminTicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status:     str | None = Field(default=None, pattern="^(open|in_progress|resolved|closed)$")
    admin_note: str | None = Field(default=None, max_length=4000)
    priority:   str | None = Field(default=None, pattern="^(low|normal|high)$")
