"""
Structured, privacy-safe hooks for Telegram channel observability.

One JSON log line per call with stable field names for future platform analytics. Never log bot
tokens, webhook secrets, message bodies, or other credentials.

**Events** (``telegram_event`` — not ``event``, reserved by structlog):

* ``telegram_message_received`` — inbound user text accepted; conversation bound; before AI.
* ``telegram_message_answered`` — after AI + outbound send attempt (see ``outbound_sent``).
* ``telegram_lead_created`` — new CRM lead from a Telegram conversation.
* ``telegram_error`` — inbound/connect/runtime failure (``error_code`` only).
* ``telegram_connect_success`` / ``telegram_connect_failure`` — owner connect lifecycle.
* ``telegram_provisioning_started`` — owner opened Telegram setup (pending row).
* ``telegram_token_validate_success`` — owner dry-run token check (no persistence).
* ``telegram_webhook_sync_success`` / ``telegram_webhook_sync_failure`` — explicit webhook refresh.

Correlators: ``channel`` (always ``telegram``), ``bot_id``, ``conversation_id``, ``telegram_chat_id``,
``telegram_update_id``, ``telegram_config_id``, ``lead_id``. Timestamps come from structlog's ISO
processor.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from app.core.logging import get_logger
from app.lib.chat_channels import CONVERSATION_CHANNEL_TELEGRAM

_LOG = get_logger("telegram_channel")

TELEGRAM_MESSAGE_RECEIVED = "telegram_message_received"
TELEGRAM_MESSAGE_ANSWERED = "telegram_message_answered"
TELEGRAM_LEAD_CREATED = "telegram_lead_created"
TELEGRAM_ERROR = "telegram_error"
TELEGRAM_CONNECT_SUCCESS = "telegram_connect_success"
TELEGRAM_CONNECT_FAILURE = "telegram_connect_failure"
TELEGRAM_PROVISIONING_STARTED = "telegram_provisioning_started"
TELEGRAM_TOKEN_VALIDATE_SUCCESS = "telegram_token_validate_success"
TELEGRAM_WEBHOOK_SYNC_SUCCESS = "telegram_webhook_sync_success"
TELEGRAM_WEBHOOK_SYNC_FAILURE = "telegram_webhook_sync_failure"

_AI_ERROR_CODE_MAX_LEN = 64


def _truncate_code(code: str | None, max_len: int = _AI_ERROR_CODE_MAX_LEN) -> str | None:
    if code is None:
        return None
    s = str(code).strip()
    return s[:max_len] if len(s) > max_len else s


def emit_telegram_channel_event(
    *,
    telegram_event: str,
    level: Literal["info", "warning", "error"] = "info",
    bot_id: UUID | str | None = None,
    conversation_id: UUID | str | None = None,
    telegram_chat_id: int | None = None,
    telegram_update_id: int | None = None,
    telegram_config_id: UUID | str | None = None,
    lead_id: UUID | str | None = None,
    error_code: str | None = None,
    inbound_chars: int | None = None,
    outbound_chars: int | None = None,
    outbound_sent: bool | None = None,
    latency_ms: int | None = None,
    ai_success: bool | None = None,
    ai_error_code: str | None = None,
    creation_reason: str | None = None,
    telegram_bot_api_user_id: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit one structured log line. Unknown or empty fields are omitted."""
    payload: dict[str, Any] = {
        "channel": CONVERSATION_CHANNEL_TELEGRAM,
        "telegram_event": telegram_event,
    }
    if bot_id is not None:
        payload["bot_id"] = str(bot_id)
    if conversation_id is not None:
        payload["conversation_id"] = str(conversation_id)
    if telegram_chat_id is not None:
        payload["telegram_chat_id"] = telegram_chat_id
    if telegram_update_id is not None:
        payload["telegram_update_id"] = telegram_update_id
    if telegram_config_id is not None:
        payload["telegram_config_id"] = str(telegram_config_id)
    if lead_id is not None:
        payload["lead_id"] = str(lead_id)
    if error_code:
        payload["error_code"] = _truncate_code(error_code, max_len=96)
    if inbound_chars is not None:
        payload["inbound_chars"] = inbound_chars
    if outbound_chars is not None:
        payload["outbound_chars"] = outbound_chars
    if outbound_sent is not None:
        payload["outbound_sent"] = outbound_sent
    if latency_ms is not None:
        payload["latency_ms"] = latency_ms
    if ai_success is not None:
        payload["ai_success"] = ai_success
    ac = _truncate_code(ai_error_code)
    if ac:
        payload["ai_error_code"] = ac
    if creation_reason:
        payload["creation_reason"] = str(creation_reason)[:128]
    if telegram_bot_api_user_id is not None:
        payload["telegram_bot_api_user_id"] = telegram_bot_api_user_id
    if extra:
        for k, v in extra.items():
            if v is not None:
                payload[k] = v

    if telegram_event in (
        TELEGRAM_ERROR,
        TELEGRAM_CONNECT_FAILURE,
        TELEGRAM_WEBHOOK_SYNC_FAILURE,
    ):
        payload["observability_signal"] = "telegram_failure"
    elif telegram_event == TELEGRAM_MESSAGE_ANSWERED and outbound_sent is False:
        payload["observability_signal"] = "telegram_delivery_failure"

    if level == "error":
        _LOG.error("telegram_channel_event", **payload)
    elif level == "warning":
        _LOG.warning("telegram_channel_event", **payload)
    else:
        _LOG.info("telegram_channel_event", **payload)


__all__ = [
    "TELEGRAM_CONNECT_FAILURE",
    "TELEGRAM_CONNECT_SUCCESS",
    "TELEGRAM_PROVISIONING_STARTED",
    "TELEGRAM_TOKEN_VALIDATE_SUCCESS",
    "TELEGRAM_WEBHOOK_SYNC_FAILURE",
    "TELEGRAM_WEBHOOK_SYNC_SUCCESS",
    "TELEGRAM_ERROR",
    "TELEGRAM_LEAD_CREATED",
    "TELEGRAM_MESSAGE_ANSWERED",
    "TELEGRAM_MESSAGE_RECEIVED",
    "emit_telegram_channel_event",
]
