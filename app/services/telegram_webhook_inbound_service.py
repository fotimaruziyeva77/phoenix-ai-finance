"""
Telegram inbound webhook runtime: parse update → conversation → :class:`~app.services.ai_service.AIService` → Bot API reply.

**Design**
    * **No dashboard auth** — access is ``X-Telegram-Bot-Api-Secret-Token`` + ``bot_id`` path (verified before this service runs).
    * **Thin HTTP** — :mod:`app.api.v1.public_telegram` delegates here; orchestration stays in this module.
    * **Sales / support AI** — identical path to the owner test chat and public widget: ``AIService.send_bot_message``, which delegates to
      :class:`~app.services.sales_conversation_orchestrator.SalesConversationOrchestrator` for ``goal_type=sales`` bots (no duplicated sales logic).
      **CRM:** sales bots use the same :mod:`app.services.sales_lead_capture_turn` + :class:`~app.models.lead.Lead` row as the widget; ``source_channel``
      is ``telegram`` from :attr:`~app.models.ai_foundation.Conversation.channel`. Optional ``from`` user hints are merged into ``collected_data_json``
      before the turn (see :func:`~app.repositories.ai_chat_repository.AIChatRepository.merge_telegram_collected_hints`).
    * **Channel** — Threads via :class:`~app.services.conversation_thread_service.ConversationThreadService`
      (``channel=telegram``, ``telegram_chat_id``); same ``AIService`` core as the widget.
    * **Privacy** — logs use ids only; no message bodies, tokens, or PII in log fields.
      Structured channel events: :mod:`app.core.telegram_channel_events`.
    * **Telegram reliability** — handler aims to return HTTP 200 after enqueue-style processing; outbound failures are logged, not raised to Starlette.

``send_reply`` is injectable for tests; production uses :func:`~app.integrations.telegram_bot_reply.send_telegram_text_to_chat`,
which applies :mod:`app.integrations.telegram_reply_format` (plain text, soft length cap, no ``parse_mode``).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Awaitable, Callable
from time import perf_counter

from sqlalchemy import select

from app.core.config import Settings
from app.core.error_tracking import capture_exception
from app.core.logging import get_logger
from app.core.telegram_channel_events import (
    TELEGRAM_ERROR,
    TELEGRAM_MESSAGE_ANSWERED,
    TELEGRAM_MESSAGE_RECEIVED,
    emit_telegram_channel_event,
)
from app.integrations.telegram_bot_api.errors import TelegramBotApiError
from app.integrations.telegram_bot_api.parse import parse_telegram_update
from app.integrations.telegram_bot_api.types import ParsedTelegramUpdate
from app.integrations.telegram_bot_reply import send_telegram_text_to_chat
from app.lib.platform_moderation import bot_is_platform_suspended
from app.lib.telegram_token_crypto import TelegramTokenCryptoError, decrypt_telegram_bot_token
from app.models.bot import Bot
from app.domain.telegram_channel_status import TELEGRAM_PROVISIONING_ACTIVE
from app.models.telegram_config import TelegramConfig
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.user_repository import UserRepository
from app.services.ai_exceptions import AIServiceError
from app.services.ai_service import AIService
from app.services.billing_exceptions import ConversationLimitExceededError
from app.services.billing_service import BillingService
from app.services.conversation_thread_service import ConversationThreadService

_LOG = get_logger(__name__)

_GENERIC_USER_FACING_FAILURE = (
    "Sorry, I couldn't complete that request. Please try again in a moment."
)

SendTelegramTextFn = Callable[..., Awaitable[None]]


async def _default_send_telegram_text(*, bot_token: str, chat_id: int, text: str) -> None:
    await send_telegram_text_to_chat(bot_token=bot_token, chat_id=chat_id, text=text)


class TelegramWebhookInboundService:
    def __init__(
        self,
        chat_repo: AIChatRepository,
        user_repo: UserRepository,
        ai_service: AIService,
        settings: Settings,
        *,
        send_telegram_text: SendTelegramTextFn | None = None,
        thread_service: ConversationThreadService | None = None,
        billing_service: BillingService | None = None,
    ) -> None:
        self._chat = chat_repo
        self._users = user_repo
        self._ai = ai_service
        self._settings = settings
        self._send_text: SendTelegramTextFn = send_telegram_text or _default_send_telegram_text
        self._threads = thread_service or ConversationThreadService(chat_repo)
        self._billing = billing_service

    async def handle_raw_update(self, *, bot_id: uuid.UUID, raw_body: bytes) -> None:
        """
        Process a verified webhook body. Swallows errors after logging (caller should still HTTP 200).
        """
        try:
            await self._handle_raw_update_inner(bot_id=bot_id, raw_body=raw_body)
        except Exception as exc:
            emit_telegram_channel_event(
                telegram_event=TELEGRAM_ERROR,
                level="error",
                bot_id=bot_id,
                error_code="inbound_unhandled",
            )
            _LOG.exception(
                "telegram_inbound_unhandled_failure",
                bot_id=str(bot_id),
            )
            capture_exception(
                exc,
                domain="telegram_inbound",
                tags={"bot_id": str(bot_id), "error_code": "inbound_unhandled"},
            )

    async def _handle_raw_update_inner(self, *, bot_id: uuid.UUID, raw_body: bytes) -> None:
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            emit_telegram_channel_event(
                telegram_event=TELEGRAM_ERROR,
                level="warning",
                bot_id=bot_id,
                error_code="json_invalid",
            )
            return

        loaded = await self._load_connected_telegram(bot_id)
        if loaded is None:
            _LOG.warning(
                "telegram_inbound_skip_no_active_channel",
                bot_id=str(bot_id),
                hint="No TelegramConfig with is_connected + active provisioning, or bot archived",
            )
            return
        cfg, bot = loaded

        try:
            parsed = parse_telegram_update(payload)
        except TelegramBotApiError:
            uid: int | None = None
            if isinstance(payload, dict):
                raw_uid = payload.get("update_id")
                if isinstance(raw_uid, int):
                    uid = raw_uid
            emit_telegram_channel_event(
                telegram_event=TELEGRAM_ERROR,
                level="warning",
                bot_id=bot_id,
                telegram_update_id=uid,
                error_code="parse_failed",
            )
            return

        text_in, chat_id = _extract_user_text_and_chat(parsed)
        if not text_in or chat_id is None:
            _LOG.info(
                "telegram_inbound_skip_no_routable_text",
                bot_id=str(bot_id),
                telegram_update_id=parsed.update_id,
                raw_kind=parsed.raw_kind,
                has_chat_id=chat_id is not None,
                hint="Need text/caption (message) or callback data + message.chat; stickers/voice ignored",
            )
            return

        owner = await self._users.get_by_id(bot.owner_id)
        if owner is None:
            emit_telegram_channel_event(
                telegram_event=TELEGRAM_ERROR,
                level="error",
                bot_id=bot_id,
                telegram_chat_id=chat_id,
                telegram_update_id=parsed.update_id,
                error_code="owner_missing",
            )
            return

        try:
            plain_token = decrypt_telegram_bot_token(cfg.bot_token_encrypted, self._settings)
        except TelegramTokenCryptoError:
            emit_telegram_channel_event(
                telegram_event=TELEGRAM_ERROR,
                level="error",
                bot_id=bot_id,
                telegram_chat_id=chat_id,
                telegram_update_id=parsed.update_id,
                error_code="token_decrypt_failed",
            )
            _LOG.warning(
                "telegram_inbound_token_decrypt_failed",
                bot_id=str(bot_id),
                telegram_chat_id=chat_id,
                telegram_update_id=parsed.update_id,
                hint="Cannot decrypt stored bot token; reconnect Telegram in dashboard or fix TELEGRAM_TOKEN_FERNET_KEY",
            )
            return

        if not owner.is_active or bot_is_platform_suspended(bot):
            emit_telegram_channel_event(
                telegram_event=TELEGRAM_ERROR,
                level="info",
                bot_id=bot_id,
                telegram_chat_id=chat_id,
                telegram_update_id=parsed.update_id,
                error_code="owner_inactive_or_bot_platform_suspended",
            )
            await self._safe_send(
                plain_token,
                chat_id,
                _GENERIC_USER_FACING_FAILURE,
                bot_id=bot_id,
                conversation_id=None,
            )
            return

        # ── Plan conversation limit enforcement ──────────────────────
        if self._billing is not None:
            from datetime import UTC, datetime
            _now = datetime.now(UTC)
            _monthly = await self._chat.count_conversations_this_month_for_owner(
                owner.id, year=_now.year, month=_now.month
            )
            try:
                await self._billing.enforce_conversation_limit(owner, _monthly)
            except ConversationLimitExceededError:
                emit_telegram_channel_event(
                    telegram_event=TELEGRAM_ERROR,
                    level="info",
                    bot_id=bot_id,
                    telegram_chat_id=chat_id,
                    telegram_update_id=parsed.update_id,
                    error_code="plan_conversation_limit_exceeded",
                )
                _LOG.info(
                    "telegram_inbound_conversation_limit_exceeded",
                    bot_id=str(bot_id),
                    owner_id=str(owner.id),
                    monthly_count=_monthly,
                )
                await self._safe_send(
                    plain_token,
                    chat_id,
                    "This bot has reached its monthly conversation limit. Please try again next month.",
                    bot_id=bot_id,
                    conversation_id=None,
                )
                return

        conv = await self._threads.get_or_create_telegram_thread(
            bot_id=bot.id,
            owner_id=bot.owner_id,
            niche_id_snapshot=(bot.niche_id or "").strip() or None,
            telegram_chat_id=chat_id,
        )

        await self._chat.merge_telegram_collected_hints(
            conv.id,
            from_username=parsed.from_user_username,
            from_first_name=parsed.from_user_first_name,
        )

        emit_telegram_channel_event(
            telegram_event=TELEGRAM_MESSAGE_RECEIVED,
            bot_id=bot.id,
            conversation_id=conv.id,
            telegram_chat_id=chat_id,
            telegram_update_id=parsed.update_id,
            inbound_chars=len(text_in),
        )

        t0 = perf_counter()
        try:
            result = await self._ai.send_bot_message(
                bot,
                owner,
                text_in,
                conversation_id=conv.id,
            )
        except AIServiceError as exc:
            latency_ms = int((perf_counter() - t0) * 1000)
            _LOG.warning(
                "telegram_inbound_ai_service_error",
                bot_id=str(bot.id),
                conversation_id=str(conv.id),
                ai_error_code=exc.client_code,
            )
            outbound_chars = len(_GENERIC_USER_FACING_FAILURE)
            sent_ok = await self._safe_send(
                plain_token,
                chat_id,
                _GENERIC_USER_FACING_FAILURE,
                bot_id=bot_id,
                conversation_id=conv.id,
            )
            emit_telegram_channel_event(
                telegram_event=TELEGRAM_MESSAGE_ANSWERED,
                bot_id=bot.id,
                conversation_id=conv.id,
                telegram_chat_id=chat_id,
                telegram_update_id=parsed.update_id,
                latency_ms=latency_ms,
                ai_success=False,
                ai_error_code=exc.client_code,
                outbound_chars=outbound_chars,
                outbound_sent=sent_ok,
            )
            return

        if not result.success:
            _LOG.warning(
                "telegram_inbound_ai_turn_failed",
                bot_id=str(bot.id),
                conversation_id=str(conv.id),
                ai_error_code=result.error_code,
                ai_error_category=result.error_category,
            )

        reply = (result.assistant_text or "").strip() if result.success else ""
        sent_ok = False
        outbound_chars = 0
        rate_limit_fallback_sent = False
        if result.success and reply:
            outbound_chars = len(reply)
            sent_ok = await self._safe_send(
                plain_token,
                chat_id,
                reply,
                bot_id=bot_id,
                conversation_id=conv.id,
            )
        elif not result.success:
            fb_rl = (self._settings.ai_telegram_gemini_rate_limit_user_message_uz or "").strip()
            if (result.error_code or "").strip() == "rate_limited" and fb_rl:
                _LOG.info(
                    "telegram_rate_limit_fallback",
                    bot_id=str(bot.id),
                    conversation_id=str(conv.id),
                    channel="telegram",
                )
                outbound_chars = len(fb_rl)
                sent_ok = await self._safe_send(
                    plain_token,
                    chat_id,
                    fb_rl,
                    bot_id=bot_id,
                    conversation_id=conv.id,
                )
                rate_limit_fallback_sent = bool(sent_ok)
            else:
                outbound_chars = len(_GENERIC_USER_FACING_FAILURE)
                sent_ok = await self._safe_send(
                    plain_token,
                    chat_id,
                    _GENERIC_USER_FACING_FAILURE,
                    bot_id=bot_id,
                    conversation_id=conv.id,
                )

        latency_ms = int((perf_counter() - t0) * 1000)
        emit_telegram_channel_event(
            telegram_event=TELEGRAM_MESSAGE_ANSWERED,
            bot_id=bot.id,
            conversation_id=conv.id,
            telegram_chat_id=chat_id,
            telegram_update_id=parsed.update_id,
            latency_ms=latency_ms,
            ai_success=result.success or rate_limit_fallback_sent,
            ai_error_code=None if rate_limit_fallback_sent else (result.error_code if not result.success else None),
            outbound_chars=outbound_chars,
            outbound_sent=sent_ok,
        )

    async def _safe_send(
        self,
        plain_token: str,
        chat_id: int,
        text: str,
        *,
        bot_id: uuid.UUID,
        conversation_id: uuid.UUID | None = None,
    ) -> bool:
        try:
            await self._send_text(bot_token=plain_token, chat_id=chat_id, text=text)
            return True
        except TelegramBotApiError:
            emit_telegram_channel_event(
                telegram_event=TELEGRAM_ERROR,
                level="warning",
                bot_id=bot_id,
                conversation_id=conversation_id,
                telegram_chat_id=chat_id,
                error_code="outbound_send_failed",
            )
            return False

    async def _load_connected_telegram(self, bot_id: uuid.UUID) -> tuple[TelegramConfig, Bot] | None:
        stmt = (
            select(TelegramConfig, Bot)
            .join(Bot, Bot.id == TelegramConfig.bot_id)
            .where(
                TelegramConfig.bot_id == bot_id,
                TelegramConfig.is_connected.is_(True),
                TelegramConfig.provisioning_status == TELEGRAM_PROVISIONING_ACTIVE,
            )
            .limit(1)
        )
        result = await self._chat.session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        cfg, bot = row[0], row[1]
        if bot.status == "archived":
            return None
        return cfg, bot


def _extract_user_text_and_chat(parsed: ParsedTelegramUpdate) -> tuple[str | None, int | None]:
    if parsed.raw_kind not in (
        "message",
        "edited_message",
        "business_message",
        "callback_query",
    ):
        return None, None
    text = (parsed.message_text or "").strip()
    if not text:
        return None, None
    cid = parsed.chat_id
    if cid is None:
        return None, None
    return text, cid
