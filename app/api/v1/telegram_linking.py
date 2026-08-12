"""Telegram account linking for per-customer lead alerts."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.user import User

router = APIRouter(tags=["telegram-linking"])

_LOG = get_logger("telegram_linking")


class TelegramLinkStatusResponse(BaseModel):
    """Current Telegram linking state for the authenticated user."""

    is_linked: bool
    telegram_chat_id: str | None = None
    linked_at: str | None = None
    link_url: str | None = None
    bot_username: str | None = None


class TelegramUnlinkResponse(BaseModel):
    success: bool


class TelegramWebhookStartBody(BaseModel):
    """Payload from the Telegram webhook when a user sends /start <code>."""

    link_code: str = Field(min_length=1, max_length=64)
    chat_id: str = Field(min_length=1, max_length=64)


class TelegramWebhookStartResponse(BaseModel):
    success: bool
    message: str


@router.get(
    "/settings/telegram",
    response_model=TelegramLinkStatusResponse,
    summary="Get Telegram linking status and deep link URL",
)
async def telegram_link_status(
    user: CurrentUser,
    session: DbSession,
) -> TelegramLinkStatusResponse:
    settings = get_settings()
    bot_username = (settings.telegram_lead_alert_bot_username or "").strip() or None

    is_linked = bool(user.telegram_chat_id)

    # Generate or refresh link code if not linked
    link_url: str | None = None
    if not is_linked and bot_username:
        code = user.telegram_link_code
        if not code:
            code = secrets.token_urlsafe(24)
            stmt = (
                update(User)
                .where(User.id == user.id)
                .values(telegram_link_code=code)
            )
            await session.execute(stmt)
            await session.commit()
        link_url = f"https://t.me/{bot_username}?start={code}"

    return TelegramLinkStatusResponse(
        is_linked=is_linked,
        telegram_chat_id=user.telegram_chat_id if is_linked else None,
        linked_at=user.telegram_linked_at.isoformat() if user.telegram_linked_at else None,
        link_url=link_url,
        bot_username=bot_username,
    )


@router.delete(
    "/settings/telegram",
    response_model=TelegramUnlinkResponse,
    summary="Unlink Telegram account",
)
async def telegram_unlink(
    user: CurrentUser,
    session: DbSession,
) -> TelegramUnlinkResponse:
    stmt = (
        update(User)
        .where(User.id == user.id)
        .values(
            telegram_chat_id=None,
            telegram_link_code=None,
            telegram_linked_at=None,
        )
    )
    await session.execute(stmt)
    await session.commit()
    _LOG.info("telegram_unlinked", user_id=str(user.id))
    return TelegramUnlinkResponse(success=True)


@router.post(
    "/webhooks/telegram-link",
    response_model=TelegramWebhookStartResponse,
    summary="Telegram bot webhook: process /start deep link code",
)
async def telegram_webhook_start(
    body: TelegramWebhookStartBody,
    session: DbSession,
) -> TelegramWebhookStartResponse:
    """
    Called by the Telegram bot webhook adapter when a user sends ``/start <link_code>``.

    Matches the code to a user, saves their ``telegram_chat_id``, and clears the code.
    This endpoint is unauthenticated (called by the Telegram webhook processor).
    """
    code = body.link_code.strip()
    chat_id = body.chat_id.strip()

    if not code or not chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="link_code and chat_id are required",
        )

    # Find user by link code
    stmt = select(User).where(User.telegram_link_code == code)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        _LOG.warning("telegram_link_code_not_found", code_prefix=code[:8])
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired link code",
        )

    # Link the account
    now = datetime.now(tz=UTC)
    update_stmt = (
        update(User)
        .where(User.id == user.id)
        .values(
            telegram_chat_id=chat_id,
            telegram_link_code=None,  # one-time use
            telegram_linked_at=now,
        )
    )
    await session.execute(update_stmt)
    await session.commit()

    _LOG.info(
        "telegram_linked",
        user_id=str(user.id),
        chat_id_last4=chat_id[-4:] if len(chat_id) >= 4 else "***",
    )

    return TelegramWebhookStartResponse(
        success=True,
        message="Telegram account linked successfully",
    )
