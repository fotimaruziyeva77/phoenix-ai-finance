"""Pydantic shapes for lead capture and CRM-style listing (API-ready)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

LeadStatusLiteral = Literal["new", "contacted", "qualified", "proposal", "won", "lost"]
LeadTemperatureLiteral = Literal["cold", "warm", "hot"]


class LeadRead(BaseModel):
    """Full lead row for GET detail and PATCH responses (dashboard CRM)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bot_id: UUID
    owner_id: UUID
    conversation_id: UUID | None = None
    niche_id: str = Field(..., max_length=120, description="Niche key at capture time.")
    lead_score: int | None = Field(default=None, ge=0, le=100, description="Model score 0–100 when set.")
    lead_temperature: LeadTemperatureLiteral | None = None
    status: LeadStatusLiteral
    name: str | None = Field(default=None, max_length=256)
    phone: str | None = Field(default=None, max_length=40)
    summary: str | None = Field(default=None, description="Short qualification summary for the owner.")
    notes: str | None = Field(default=None, description="Owner-only CRM notes (editable via PATCH /status).")
    assignee_user_id: UUID | None = Field(
        default=None,
        description="Optional assignee (registered user id); null clears assignment.",
    )
    source_channel: str | None = Field(default=None, max_length=64, description="Capture channel (e.g. telegram).")
    collected_data_json: dict[str, object] | None = Field(
        default=None,
        description="Structured fields collected during the conversation (JSON object).",
    )
    owner_inbox_routed_at: datetime | None = Field(
        default=None,
        description="Set when owner delivery router confirmed CRM inbox visibility for this lead.",
    )
    telegram_delivery_status: str | None = Field(
        default=None,
        description=(
            "Telegram new-lead alert outcome: skipped_not_configured | skipped_no_target | "
            "skipped_owner_pref | delivered | failed"
        ),
    )
    telegram_delivery_attempts: int = Field(default=0, ge=0)
    telegram_delivery_updated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class LeadListItem(BaseModel):
    """Table / pipeline card projection."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bot_id: UUID
    conversation_id: UUID | None = None
    niche_id: str
    status: LeadStatusLiteral
    lead_temperature: LeadTemperatureLiteral | None = None
    lead_score: int | None = Field(default=None, ge=0, le=100)
    name: str | None = None
    phone: str | None = None
    summary: str | None = Field(
        default=None,
        description="Optional short preview; UI may truncate.",
    )
    source_channel: str | None = None
    owner_inbox_routed_at: datetime | None = None
    telegram_delivery_status: str | None = None
    telegram_delivery_attempts: int = Field(default=0, ge=0)
    telegram_delivery_updated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class LeadUpdateStatus(BaseModel):
    """Patch pipeline stage (and optionally temperature) from dashboards."""

    status: LeadStatusLiteral
    lead_temperature: LeadTemperatureLiteral | None = None


class LeadStatusPatchBody(BaseModel):
    """Request body for ``PATCH /leads/{id}/status`` (status required; optional CRM fields)."""

    model_config = ConfigDict(extra="forbid")

    status: LeadStatusLiteral
    lead_temperature: LeadTemperatureLiteral | None = None
    notes: str | None = Field(default=None, max_length=16_000)
    assignee_user_id: UUID | None = None


class LeadPipelinePatch(BaseModel):
    """
    Partial CRM update. Only fields present in the request body are applied (router uses
    ``model_fields_set``). At least one field must be set.
    """

    model_config = ConfigDict(extra="forbid")

    status: LeadStatusLiteral | None = None
    lead_temperature: LeadTemperatureLiteral | None = None
    notes: str | None = Field(default=None, max_length=16_000)
    assignee_user_id: UUID | None = None


class LeadCreateInternal(BaseModel):
    """
    Service-layer insert payload. Not exposed as a public “submit lead” API by default —
    creation should run inside trusted code paths (e.g. post-qualification hook).
    """

    model_config = ConfigDict(extra="forbid")

    bot_id: UUID
    owner_id: UUID
    conversation_id: UUID | None = None
    niche_id: str = Field(..., max_length=120)
    lead_score: int | None = Field(default=None, ge=0, le=100)
    lead_temperature: LeadTemperatureLiteral | None = None
    status: LeadStatusLiteral = "new"
    name: str | None = Field(default=None, max_length=256)
    phone: str | None = Field(default=None, max_length=40)
    summary: str | None = None
    source_channel: str | None = Field(default=None, max_length=64)
    collected_data_json: dict[str, object] | None = None


class LeadListResponse(BaseModel):
    """Paginated list envelope (caller fills ``total`` when available)."""

    items: list[LeadListItem]
    total: int = Field(..., ge=0)
    next_cursor: str | None = Field(
        default=None,
        description="Opaque cursor for the next page (cursor-based pagination). "
        "Null when there are no more results.",
    )
    has_more: bool = Field(
        default=False,
        description="True when there is at least one more page after this one.",
    )


class LeadEventRead(BaseModel):
    """One append-only CRM timeline row."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    lead_id: UUID
    event_type: str
    actor_type: str
    actor_id: UUID | None = None
    old_value: str | None = None
    new_value: str | None = None
    metadata: dict[str, object] | None = Field(
        default=None,
        validation_alias="metadata_json",
    )
    created_at: datetime


class LeadEventListResponse(BaseModel):
    items: list[LeadEventRead]
    total: int = Field(..., ge=0)
