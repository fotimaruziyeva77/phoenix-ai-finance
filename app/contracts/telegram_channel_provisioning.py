"""
Owner-facing Telegram channel provisioning port.

:class:`TelegramConfigService` is the production implementation. Depend on this protocol
in routers or tests when you need a narrow, mock-friendly surface.
"""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from app.integrations.telegram_bot_verify import TelegramBotVerificationResult
from app.models.user import User
from app.schemas.telegram_config import (
    BotTelegramStatusResponse,
    TelegramConfigRead,
    TelegramWebhookBulkResyncResponse,
)


@runtime_checkable
class TelegramChannelProvisioningPort(Protocol):
    async def start_telegram_channel_provisioning(
        self,
        owner: User,
        bot_id: uuid.UUID,
    ) -> BotTelegramStatusResponse: ...

    async def connect_telegram_for_bot(
        self,
        owner: User,
        bot_id: uuid.UUID,
        token: str,
    ) -> TelegramConfigRead: ...

    async def validate_telegram_token_for_bot(
        self,
        owner: User,
        bot_id: uuid.UUID,
        token: str,
    ) -> TelegramBotVerificationResult: ...

    async def sync_telegram_webhook_for_bot(
        self,
        owner: User,
        bot_id: uuid.UUID,
    ) -> BotTelegramStatusResponse: ...

    async def resync_all_telegram_webhooks_for_owner(
        self,
        owner: User,
    ) -> TelegramWebhookBulkResyncResponse: ...

    async def get_telegram_integration_status(
        self,
        owner: User,
        bot_id: uuid.UUID,
    ) -> BotTelegramStatusResponse: ...

    async def disconnect_telegram_for_bot(self, owner: User, bot_id: uuid.UUID) -> None: ...

    async def verify_telegram_webhook_request(
        self,
        bot_id: uuid.UUID,
        *,
        secret_header_value: str | None,
    ) -> bool: ...
