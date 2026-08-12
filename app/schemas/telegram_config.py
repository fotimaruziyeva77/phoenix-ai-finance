"""HTTP shapes for Telegram integration (no raw token in responses)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.telegram_channel_status import (
    PROVISIONING_LAST_ERROR_META_KEY,
    TELEGRAM_CHANNEL_ACTIVE,
    TELEGRAM_CHANNEL_DRAFT,
    TELEGRAM_CHANNEL_FAILED_VALIDATION,
    TELEGRAM_CHANNEL_PENDING,
    TELEGRAM_PROVISIONING_ACTIVE,
    TELEGRAM_PROVISIONING_FAILED_VALIDATION,
    TelegramChannelStatus,
)
from app.models.telegram_config import TelegramConfig


class TelegramConfigRead(BaseModel):
    """Full row for authenticated owner services (ORM); excludes decrypted token."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bot_id: UUID
    owner_id: UUID
    has_stored_bot_token: bool = Field(
        default=False,
        description="True when ``bot_token_encrypted`` is non-empty (from ORM property).",
    )
    provisioning_status: str = Field(default=TELEGRAM_CHANNEL_PENDING, max_length=32)
    bot_username: str | None = Field(default=None, max_length=64)
    webhook_url: str | None = Field(default=None, max_length=2048)
    is_connected: bool
    last_verified_at: datetime | None = None
    metadata_json: dict[str, object] | None = None
    created_at: datetime
    updated_at: datetime


class TelegramConfigConnectRequest(BaseModel):
    """Supply bot token once; server encrypts before persistence."""

    model_config = ConfigDict(extra="forbid")

    bot_token: str = Field(
        min_length=10,
        max_length=128,
        description="Telegram BotFather token (digits:alphanumeric).",
    )
    bot_username: str | None = Field(
        default=None,
        max_length=64,
        description="Optional @username without leading @.",
    )

    @field_validator("bot_username")
    @classmethod
    def strip_at_username(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        if s.startswith("@"):
            s = s[1:].strip()
        return s or None


class TelegramConfigStatusResponse(BaseModel):
    """Dashboard / health: safe subset, no secrets."""

    bot_id: UUID
    is_configured: bool = Field(description="Row exists with an encrypted token stored.")
    is_connected: bool
    bot_username: str | None = None
    webhook_configured: bool = Field(description="True when webhook_url is non-empty.")
    last_verified_at: datetime | None = None


class TelegramConfigUpdate(BaseModel):
    """Partial update: webhook refresh, pause, metadata, or token rotation."""

    model_config = ConfigDict(extra="forbid")

    bot_token: str | None = Field(
        default=None,
        min_length=10,
        max_length=128,
        description="Replace stored token (re-encrypted); omit to leave unchanged.",
    )
    bot_username: str | None = Field(default=None, max_length=64)
    webhook_url: str | None = Field(default=None, max_length=2048)
    is_connected: bool | None = None
    last_verified_at: datetime | None = None
    metadata_json: dict[str, object] | None = None

    @field_validator("bot_username")
    @classmethod
    def strip_at_username(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        if s.startswith("@"):
            s = s[1:].strip()
        return s or None


class BotTelegramConnectRequest(BaseModel):
    """Owner API body: BotFather token only (server verifies with Telegram; never returned)."""

    model_config = ConfigDict(extra="forbid")

    bot_token: str = Field(
        min_length=10,
        max_length=128,
        description="Telegram BotFather token.",
    )


class BotTelegramTokenValidateResponse(BaseModel):
    """Result of a non-persisting token check (``POST .../telegram/token/validate``)."""

    valid: Literal[True] = True
    bot_username: str | None = Field(
        default=None,
        description="Username from Telegram getMe (no leading @), if present.",
    )
    telegram_bot_id: int = Field(
        ...,
        description="Telegram bot user id from getMe (public identifier).",
    )


class TelegramWebhookBulkResyncItem(BaseModel):
    """One bot outcome from ``POST .../telegram/webhooks/resync-all``."""

    bot_id: UUID
    success: bool = Field(description="True when ``setWebhook`` succeeded for this bot.")
    error_code: str | None = Field(
        default=None,
        description="Stable domain code from :class:`~app.services.telegram_config_exceptions.TelegramConfigServiceError` subclasses.",
    )
    error_message: str | None = Field(default=None, description="Human-readable reason when ``success`` is false.")


class TelegramWebhookBulkResyncResponse(BaseModel):
    """Owner-scoped bulk webhook refresh (e.g. after changing ``APP_PUBLIC_API_BASE_URL`` / tunnel)."""

    eligible_count: int = Field(
        ge=0,
        description="Bots with stored token, active provisioning, connected, and not archived.",
    )
    succeeded: int = Field(ge=0)
    failed: int = Field(ge=0)
    results: list[TelegramWebhookBulkResyncItem] = Field(default_factory=list)


class BotTelegramStatusResponse(BaseModel):
    """
    Owner API snapshot for dashboard (connect + status).

    * ``channel_status`` — canonical UX state machine (``draft`` only when no ``telegram_configs`` row).
    * ``configured`` — a validated bot token ciphertext is stored (Telegram is credentialed).
    * ``connected`` — same as ``channel_status == \"active\"`` (token + webhook OK); use for legacy checks.
    """

    channel_status: TelegramChannelStatus = Field(
        description="draft | channel_pending | active | failed_validation",
    )
    configured: bool = Field(description="Encrypted bot token is stored for this BotForge bot.")
    connected: bool = Field(
        description="Telegram channel is live: valid token and webhook registered (mirrors active).",
    )
    bot_username: str | None = Field(default=None, max_length=64)
    last_verified_at: datetime | None = None
    webhook_url_configured: bool = Field(
        default=False,
        description="A webhook URL is stored (optional ops signal).",
    )
    last_error_code: str | None = Field(
        default=None,
        description="Last provisioning failure domain code (e.g. invalid token / webhook), if any.",
    )


def telegram_row_has_stored_token(row: TelegramConfig) -> bool:
    return bool((row.bot_token_encrypted or "").strip())


def resolve_telegram_channel_status(row: TelegramConfig | None) -> TelegramChannelStatus:
    if row is None:
        return TELEGRAM_CHANNEL_DRAFT
    ps = (row.provisioning_status or "").strip() or TELEGRAM_CHANNEL_PENDING
    if ps == TELEGRAM_PROVISIONING_FAILED_VALIDATION:
        return TELEGRAM_CHANNEL_FAILED_VALIDATION
    has_token = telegram_row_has_stored_token(row)
    if (
        has_token
        and row.is_connected
        and ps == TELEGRAM_PROVISIONING_ACTIVE
    ):
        return TELEGRAM_CHANNEL_ACTIVE
    return TELEGRAM_CHANNEL_PENDING


def _provisioning_error_from_metadata(meta: dict[str, object] | None) -> str | None:
    if not meta:
        return None
    raw = meta.get(PROVISIONING_LAST_ERROR_META_KEY)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def bot_telegram_status_from_orm_row(row: TelegramConfig) -> BotTelegramStatusResponse:
    wh = (row.webhook_url or "").strip()
    ch = resolve_telegram_channel_status(row)
    has_token = telegram_row_has_stored_token(row)
    return BotTelegramStatusResponse(
        channel_status=ch,
        configured=has_token,
        connected=(ch == TELEGRAM_CHANNEL_ACTIVE),
        bot_username=row.bot_username,
        last_verified_at=row.last_verified_at,
        webhook_url_configured=bool(wh),
        last_error_code=_provisioning_error_from_metadata(row.metadata_json),
    )


def bot_telegram_status_from_read(read: TelegramConfigRead) -> BotTelegramStatusResponse:
    """Build status from :class:`TelegramConfigRead` (expects ``has_stored_bot_token`` from ORM)."""
    wh = (read.webhook_url or "").strip()
    ch: TelegramChannelStatus
    if read.provisioning_status == TELEGRAM_PROVISIONING_FAILED_VALIDATION:
        ch = TELEGRAM_CHANNEL_FAILED_VALIDATION
    elif (
        read.has_stored_bot_token
        and read.is_connected
        and read.provisioning_status == TELEGRAM_PROVISIONING_ACTIVE
    ):
        ch = TELEGRAM_CHANNEL_ACTIVE
    else:
        ch = TELEGRAM_CHANNEL_PENDING
    return BotTelegramStatusResponse(
        channel_status=ch,
        configured=read.has_stored_bot_token,
        connected=(ch == TELEGRAM_CHANNEL_ACTIVE),
        bot_username=read.bot_username,
        last_verified_at=read.last_verified_at,
        webhook_url_configured=bool(wh),
        last_error_code=_provisioning_error_from_metadata(read.metadata_json),
    )


def bot_telegram_status_disconnected() -> BotTelegramStatusResponse:
    return BotTelegramStatusResponse(
        channel_status=TELEGRAM_CHANNEL_DRAFT,
        configured=False,
        connected=False,
        bot_username=None,
        last_verified_at=None,
        webhook_url_configured=False,
        last_error_code=None,
    )


def telegram_config_status_from_orm(row: TelegramConfig) -> TelegramConfigStatusResponse:
    """Build a safe status DTO (no token fields)."""
    wh = (row.webhook_url or "").strip()
    return TelegramConfigStatusResponse(
        bot_id=row.bot_id,
        is_configured=telegram_row_has_stored_token(row),
        is_connected=row.is_connected,
        bot_username=row.bot_username,
        webhook_configured=bool(wh),
        last_verified_at=row.last_verified_at,
    )
