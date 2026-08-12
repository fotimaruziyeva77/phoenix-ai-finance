"""Telegram channel provisioning states (API + persistence)."""

from __future__ import annotations

from typing import Literal

# Returned by owner APIs (includes synthetic ``draft`` when no ``telegram_configs`` row).
TelegramChannelStatus = Literal["draft", "channel_pending", "active", "failed_validation"]

# Values stored on ``TelegramConfig.provisioning_status`` (never ``draft``).
TelegramProvisioningStatus = Literal["channel_pending", "active", "failed_validation"]

TELEGRAM_CHANNEL_DRAFT: TelegramChannelStatus = "draft"
TELEGRAM_CHANNEL_PENDING: TelegramChannelStatus = "channel_pending"
TELEGRAM_CHANNEL_ACTIVE: TelegramChannelStatus = "active"
TELEGRAM_CHANNEL_FAILED_VALIDATION: TelegramChannelStatus = "failed_validation"

TELEGRAM_PROVISIONING_CHANNEL_PENDING: TelegramProvisioningStatus = "channel_pending"
TELEGRAM_PROVISIONING_ACTIVE: TelegramProvisioningStatus = "active"
TELEGRAM_PROVISIONING_FAILED_VALIDATION: TelegramProvisioningStatus = "failed_validation"

PROVISIONING_LAST_ERROR_META_KEY = "provisioning_last_error_code"
