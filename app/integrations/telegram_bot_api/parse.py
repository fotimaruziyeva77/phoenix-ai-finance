"""
Parse Telegram ``Update`` JSON into a small struct.

Raises :class:`~app.integrations.telegram_bot_api.errors.TelegramBotApiError` with kind ``parse``.
"""

from __future__ import annotations

from typing import Any

from app.integrations.telegram_bot_api.errors import TelegramApiErrorKind, TelegramBotApiError
from app.integrations.telegram_bot_api.types import ParsedTelegramUpdate


def _chat_id_from_message(msg: dict[str, Any]) -> int | None:
    chat = msg.get("chat")
    if not isinstance(chat, dict):
        return None
    cid = chat.get("id")
    return int(cid) if isinstance(cid, int) else None


def _text_from_message(msg: dict[str, Any]) -> str | None:
    """Prefer ``text``; fall back to ``caption`` (photos/videos with caption, no text)."""
    t = msg.get("text")
    if isinstance(t, str) and t.strip():
        return t
    c = msg.get("caption")
    if isinstance(c, str) and c.strip():
        return c
    return None


def _from_user_hints(msg: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return ``(username, first_name)`` from Bot API ``User`` (no PII beyond what Telegram sends)."""
    fu = msg.get("from")
    if not isinstance(fu, dict):
        return None, None
    un = fu.get("username")
    fn = fu.get("first_name")
    username = str(un).strip()[:64] if isinstance(un, str) and str(un).strip() else None
    first = str(fn).strip()[:128] if isinstance(fn, str) and str(fn).strip() else None
    return username, first


def parse_telegram_update(payload: object) -> ParsedTelegramUpdate:
    """
    Validate and extract a minimal update shape from webhook JSON body.

    Args:
        payload: Parsed JSON (``dict``) or a string of JSON (will not be logged here).

    Raises:
        TelegramBotApiError: PARSE kind for malformed payloads.
    """
    if isinstance(payload, str):
        import json

        try:
            payload = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise TelegramBotApiError(
                TelegramApiErrorKind.PARSE,
                "Update payload is not valid JSON.",
            ) from exc

    if not isinstance(payload, dict):
        raise TelegramBotApiError(
            TelegramApiErrorKind.PARSE,
            "Update payload is not a JSON object.",
        )

    uid = payload.get("update_id")
    if not isinstance(uid, int):
        raise TelegramBotApiError(
            TelegramApiErrorKind.PARSE,
            "Update is missing a valid update_id.",
        )

    if "message" in payload and isinstance(payload["message"], dict):
        msg = payload["message"]
        u_hint, fn_hint = _from_user_hints(msg)
        return ParsedTelegramUpdate(
            update_id=uid,
            raw_kind="message",
            message_text=_text_from_message(msg),
            chat_id=_chat_id_from_message(msg),
            from_user_username=u_hint,
            from_user_first_name=fn_hint,
        )

    if "edited_message" in payload and isinstance(payload["edited_message"], dict):
        msg = payload["edited_message"]
        u_hint, fn_hint = _from_user_hints(msg)
        return ParsedTelegramUpdate(
            update_id=uid,
            raw_kind="edited_message",
            message_text=_text_from_message(msg),
            chat_id=_chat_id_from_message(msg),
            from_user_username=u_hint,
            from_user_first_name=fn_hint,
        )

    if "business_message" in payload and isinstance(payload["business_message"], dict):
        msg = payload["business_message"]
        u_hint, fn_hint = _from_user_hints(msg)
        return ParsedTelegramUpdate(
            update_id=uid,
            raw_kind="business_message",
            message_text=_text_from_message(msg),
            chat_id=_chat_id_from_message(msg),
            from_user_username=u_hint,
            from_user_first_name=fn_hint,
        )

    if "callback_query" in payload and isinstance(payload["callback_query"], dict):
        cq = payload["callback_query"]
        msg = cq.get("message") if isinstance(cq.get("message"), dict) else None
        chat_id = _chat_id_from_message(msg) if msg else None
        data = cq.get("data")
        synthetic = str(data).strip() if isinstance(data, str) and data.strip() else None
        u_hint, fn_hint = _from_user_hints(cq) if isinstance(cq, dict) else (None, None)
        return ParsedTelegramUpdate(
            update_id=uid,
            raw_kind="callback_query",
            message_text=synthetic,
            chat_id=chat_id,
            from_user_username=u_hint,
            from_user_first_name=fn_hint,
        )

    return ParsedTelegramUpdate(
        update_id=uid,
        raw_kind="unknown",
        message_text=None,
        chat_id=None,
    )
