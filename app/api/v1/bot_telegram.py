"""Owner-scoped Telegram Bot integration (dashboard).

**State machine (``BotTelegramStatusResponse.channel_status``)**

- ``draft`` — no ``telegram_configs`` row (user has not started Telegram setup).
- ``channel_pending`` — row exists; token missing and/or webhook not registered successfully yet.
- ``active`` — encrypted token stored, Telegram accepted ``setWebhook``, ``connected`` is true.
- ``failed_validation`` — token verification failed before any ciphertext was stored; see
  ``last_error_code``. (A bad reconnect while a valid token already exists leaves the prior row
  unchanged and returns an error without flipping to this state.)

**Errors (standard envelope, ``category``: ``telegram``)**

- ``telegram_token_invalid`` (422) — bad or rejected BotFather token.
- ``telegram_webhook_registration_failed`` (502) — ``setWebhook`` rejected after a valid token.
- ``telegram_bot_already_attached`` (409) — this Telegram bot id is already linked to another
  BotForge bot.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import BillingServiceDep, CurrentUser, TelegramConfigServiceDep
from app.schemas.telegram_config import (
    BotTelegramConnectRequest,
    BotTelegramStatusResponse,
    BotTelegramTokenValidateResponse,
    TelegramWebhookBulkResyncResponse,
    bot_telegram_status_from_read,
)

router = APIRouter(tags=["bots"])


@router.post(
    "/bots/telegram/webhooks/resync-all",
    response_model=TelegramWebhookBulkResyncResponse,
    summary="Re-register Telegram webhooks for every connected bot in your workspace",
    description=(
        "Calls Telegram ``setWebhook`` for each bot that has a stored token and is marked connected, "
        "using the current ``APP_PUBLIC_API_BASE_URL``. Use after changing a dev tunnel or API base URL "
        "so the dashboard stays curl-free."
    ),
)
async def resync_all_workspace_telegram_webhooks(
    user: CurrentUser,
    telegram_service: TelegramConfigServiceDep,
) -> TelegramWebhookBulkResyncResponse:
    return await telegram_service.resync_all_telegram_webhooks_for_owner(user)


@router.post(
    "/bots/{bot_id}/telegram/connect",
    response_model=BotTelegramStatusResponse,
    summary="Connect Telegram bot (verify token, encrypt at rest)",
    description=(
        "Calls Telegram getMe, stores Fernet-encrypted token, registers webhook, then returns "
        "``active`` only if both token verification and setWebhook succeed."
    ),
)
async def connect_bot_telegram(
    bot_id: UUID,
    body: BotTelegramConnectRequest,
    user: CurrentUser,
    telegram_service: TelegramConfigServiceDep,
    billing_service: BillingServiceDep,
) -> BotTelegramStatusResponse:
    # Enforce plan — Free users cannot connect Telegram
    await billing_service.enforce_telegram_access(user)
    read = await telegram_service.connect_telegram_for_bot(user, bot_id, body.bot_token)
    return bot_telegram_status_from_read(read)


@router.post(
    "/bots/{bot_id}/telegram/token/validate",
    response_model=BotTelegramTokenValidateResponse,
    summary="Validate bot token without saving or calling setWebhook",
    description=(
        "Runs getMe and duplicate-bot checks only. Use for UX feedback before connect; "
        "does not move the channel to ``active``."
    ),
)
async def validate_bot_telegram_token(
    bot_id: UUID,
    body: BotTelegramConnectRequest,
    user: CurrentUser,
    telegram_service: TelegramConfigServiceDep,
    billing_service: BillingServiceDep,
) -> BotTelegramTokenValidateResponse:
    await billing_service.enforce_telegram_access(user)
    result = await telegram_service.validate_telegram_token_for_bot(user, bot_id, body.bot_token)
    return BotTelegramTokenValidateResponse(
        valid=True,
        bot_username=result.username,
        telegram_bot_id=result.telegram_bot_id,
    )


@router.post(
    "/bots/{bot_id}/telegram/provisioning/start",
    response_model=BotTelegramStatusResponse,
    summary="Start Telegram channel setup (pending row, no token yet)",
    description="Creates a ``channel_pending`` row so the UI can show in-progress setup without a token.",
)
async def start_bot_telegram_provisioning(
    bot_id: UUID,
    user: CurrentUser,
    telegram_service: TelegramConfigServiceDep,
    billing_service: BillingServiceDep,
) -> BotTelegramStatusResponse:
    await billing_service.enforce_telegram_access(user)
    return await telegram_service.start_telegram_channel_provisioning(user, bot_id)


@router.post(
    "/bots/{bot_id}/telegram/webhook/sync",
    response_model=BotTelegramStatusResponse,
    summary="Re-register Telegram webhook using the stored token",
    description=(
        "Idempotent recovery after URL or infrastructure changes. Requires a stored encrypted token; "
        "returns ``telegram_channel_not_ready`` if the bot was never connected with a valid token."
    ),
)
async def sync_bot_telegram_webhook(
    bot_id: UUID,
    user: CurrentUser,
    telegram_service: TelegramConfigServiceDep,
) -> BotTelegramStatusResponse:
    return await telegram_service.sync_telegram_webhook_for_bot(user, bot_id)


@router.get(
    "/bots/{bot_id}/telegram/status",
    response_model=BotTelegramStatusResponse,
    summary="Telegram integration status (no secrets)",
    description="Canonical fields for dashboard badges: ``channel_status``, ``configured``, ``connected``.",
)
async def get_bot_telegram_status(
    bot_id: UUID,
    user: CurrentUser,
    telegram_service: TelegramConfigServiceDep,
) -> BotTelegramStatusResponse:
    return await telegram_service.get_telegram_integration_status(user, bot_id)


@router.post(
    "/bots/{bot_id}/telegram/disconnect",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect Telegram bot (remove stored credentials)",
)
async def disconnect_bot_telegram(
    bot_id: UUID,
    user: CurrentUser,
    telegram_service: TelegramConfigServiceDep,
) -> None:
    await telegram_service.disconnect_telegram_for_bot(user, bot_id)
