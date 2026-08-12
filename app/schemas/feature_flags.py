"""Feature flag request/response schemas (superadmin only)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FeatureFlagRead(BaseModel):
    """Full feature flag row as seen by superadmin."""

    id: UUID
    key: str
    is_enabled: bool
    target_plan: str | None = Field(
        default=None,
        description="NULL = all plans; plan slug = scoped to that tier.",
    )
    target_user_ids: list[str] | None = None
    target_user_emails: list[str] | None = None
    description: str | None = None
    updated_by_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class FeatureFlagCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r"^[a-z0-9_]+$",
        description="Snake_case identifier, e.g. 'advanced_analytics'.",
    )
    description: str | None = Field(default=None, max_length=512)
    is_enabled: bool = Field(default=False)
    target_plan: str | None = Field(
        default=None,
        description="free | starter | pro | business | enterprise | null (global).",
    )
    target_user_emails: list[str] | None = Field(
        default=None,
        description="User emails to target. Resolved to UUIDs server-side.",
    )


class FeatureFlagUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_enabled: bool | None = None
    description: str | None = Field(default=None, max_length=512)
    target_plan: str | None = Field(default=None)
    clear_target_plan: bool = Field(
        default=False,
        description="Set to true to remove plan scope (make global).",
    )
    target_user_emails: list[str] | None = Field(default=None)
    clear_target_users: bool = Field(
        default=False,
        description="Set to true to remove user-level targeting.",
    )


class FeatureFlagListResponse(BaseModel):
    items: list[FeatureFlagRead]
    total: int = Field(ge=0)
