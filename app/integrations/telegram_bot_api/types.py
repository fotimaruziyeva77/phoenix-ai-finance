"""Typed results for Telegram Bot API client (safe to log; no secrets)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TelegramGetMeResult:
    """Subset of Bot API ``User`` for the authenticated bot."""

    bot_user_id: int
    is_bot: bool
    username: str | None
    first_name: str | None


@dataclass(frozen=True, slots=True)
class TelegramSendMessageResult:
    """Minimal sendMessage success payload."""

    message_id: int
    chat_id: int


@dataclass(frozen=True, slots=True)
class ParsedTelegramUpdate:
    """
    Narrow view of an ``Update`` for routing (not a full Bot API mirror).

    ``raw_kind`` is a coarse label: ``message``, ``edited_message``, ``business_message``,
    ``callback_query`` (``message_text`` from ``data`` when present), ``unknown``.

    ``from_user_*`` are taken from ``message.from`` / ``edited_message.from`` when present (private
    chats); used to seed :attr:`~app.models.ai_foundation.Conversation.collected_data_json` for CRM
    without a separate Telegram-only lead path.
    """

    update_id: int
    raw_kind: str
    message_text: str | None
    chat_id: int | None
    from_user_username: str | None = None
    from_user_first_name: str | None = None
