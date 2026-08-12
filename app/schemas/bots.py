"""Bot API schemas."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.ai_providers.registry import registered_provider_ids

ALLOWED_GOAL_TYPES = ("support", "sales", "faq", "consulting")
ALLOWED_BOT_STATUS = ("draft", "active", "paused", "archived", "channel_pending")
InitialChannel = Literal["web", "telegram", "both"]
_STATUS_PATTERN = r"^(draft|active|paused|archived|channel_pending)$"

DEFAULT_AI_PROVIDER = "gemini"
_MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]{0,127}$")
_TEMP_MIN = 0.0
_TEMP_MAX = 2.0
_MAX_OUT_MIN = 1
_MAX_OUT_MAX = 8192


def _normalize_provider_key(value: str) -> str:
    return value.strip().lower()


def _validate_provider_key(key: str) -> str:
    k = _normalize_provider_key(key)
    if not k:
        raise ValueError("provider_name cannot be empty")
    if k not in registered_provider_ids():
        raise ValueError("provider_name is not supported for this deployment")
    return k


class BotCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    niche_id: str = Field(..., min_length=1, max_length=120)
    goal_type: str = Field(..., pattern="^(support|sales|faq|consulting)$")
    status: str = Field(default="draft", pattern=_STATUS_PATTERN)
    welcome_message: str | None = Field(default=None, max_length=1024)
    tone: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, max_length=16)
    short_description: str | None = Field(default=None, max_length=300)
    provider_name: str = Field(default=DEFAULT_AI_PROVIDER, max_length=64)
    model_name: str | None = Field(default=None, max_length=128)
    temperature: float | None = Field(default=None, ge=_TEMP_MIN, le=_TEMP_MAX)
    max_output_tokens: int | None = Field(default=None, ge=_MAX_OUT_MIN, le=_MAX_OUT_MAX)
    initial_channel: InitialChannel | None = Field(
        default=None,
        description="When set, server derives bot status and primary_channel (legacy clients omit).",
    )
    telegram_bot_token: str | None = Field(
        default=None,
        max_length=256,
        description="Optional BotFather token when initial_channel is telegram or both; verified before active.",
    )

    @model_validator(mode="after")
    def validate_channel_token_combo(self) -> Self:
        tok = (self.telegram_bot_token or "").strip() or None
        self.telegram_bot_token = tok
        if self.initial_channel is None and self.telegram_bot_token:
            raise ValueError("telegram_bot_token requires initial_channel telegram or both")
        if self.initial_channel == "web" and self.telegram_bot_token:
            raise ValueError("telegram_bot_token must not be set when initial_channel is web")
        return self

    @field_validator("provider_name")
    @classmethod
    def validate_provider_name(cls, v: str) -> str:
        return _validate_provider_key(v)

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        if not s:
            return None
        if not _MODEL_NAME_RE.fullmatch(s):
            raise ValueError(
                "model_name must be 1–128 chars, start with alphanumeric, "
                "and use only letters, digits, dots, underscores, or hyphens",
            )
        return s


class BotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    niche_id: str | None = Field(default=None, min_length=1, max_length=120)
    goal_type: str | None = Field(default=None, pattern="^(support|sales|faq|consulting)$")
    status: str | None = Field(default=None, pattern=_STATUS_PATTERN)
    welcome_message: str | None = Field(default=None, max_length=1024)
    tone: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, max_length=16)
    short_description: str | None = Field(default=None, max_length=300)
    provider_name: str | None = Field(default=None, max_length=64)
    model_name: str | None = Field(default=None, max_length=128)
    temperature: float | None = Field(default=None, ge=_TEMP_MIN, le=_TEMP_MAX)
    max_output_tokens: int | None = Field(default=None, ge=_MAX_OUT_MIN, le=_MAX_OUT_MAX)

    @field_validator("provider_name")
    @classmethod
    def validate_provider_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _validate_provider_key(v)

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        if not s:
            return None
        if not _MODEL_NAME_RE.fullmatch(s):
            raise ValueError(
                "model_name must be 1–128 chars, start with alphanumeric, "
                "and use only letters, digits, dots, underscores, or hyphens",
            )
        return s


class BotListItem(BaseModel):
    """Single bot row for dashboard list views."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    niche: str | None = None
    niche_id: str
    goal_type: str
    status: str = Field(default="draft", pattern=_STATUS_PATTERN)
    primary_channel: str | None = Field(
        default=None,
        description="web | telegram | both when set from onboarding; null for legacy bots.",
    )
    channel_count: int = Field(0, ge=0, description="Number of connected channels")
    updated_at: datetime | None = None


class BotListResponse(BaseModel):
    items: list[BotListItem]


class BotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    owner_id: UUID
    name: str
    niche_id: str
    goal_type: str
    status: str
    primary_channel: str | None = None
    welcome_message: str | None = None
    tone: str | None = None
    language: str | None = None
    short_description: str | None = None
    provider_name: str
    model_name: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    created_at: datetime
    updated_at: datetime
