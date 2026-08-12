"""
Telegram **outbound** shaping for AI replies (webhook path only).

**Rationale**

* **Separation** — The model and :class:`~app.services.ai_service.AIService` stay channel-agnostic; this
  layer runs immediately before :func:`~app.integrations.telegram_bot_reply.send_telegram_text_to_chat`.
* **Safety** — Plain text only (no ``parse_mode``): avoids broken HTML/Markdown if the model emits ``<``,
  ``*``, or ``_`` characters. Telegram still renders newlines and readable paragraphs.
* **Mobile / UX** — Soft cap keeps answers skimmable; hard cap defers to :data:`TELEGRAM_MESSAGE_MAX_CHARS`.
* **Hygiene** — Strips control characters and lines that look like leaked internal JSON keys (e.g. sales
  capture flags), never re-injecting metadata into the user-visible string.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Final

# Comfortable read on phones; still below Telegram’s 4096 hard limit after formatting.
TELEGRAM_REPLY_SOFT_MAX_CHARS: Final[int] = 2400

# Lines containing these substrings are dropped (unlikely in legitimate user-facing copy).
_INTERNAL_LINE_MARKERS: Final[tuple[str, ...]] = (
    "__lead_capture_done",
    "__captured_lead_id",
    '"__lead_capture',
    "'__lead_capture",
)


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _strip_disallowed_controls(text: str) -> str:
    """Keep tab/newline; drop other C0 controls and most Cc characters."""
    out: list[str] = []
    for ch in text:
        o = ord(ch)
        if ch in "\n\t":
            out.append(ch)
            continue
        if o < 32 or o == 127:
            continue
        if unicodedata.category(ch) == "Cc":
            continue
        out.append(ch)
    return "".join(out)


def _collapse_blank_lines(text: str, *, max_consecutive: int = 1) -> str:
    if max_consecutive < 1:
        max_consecutive = 1
    lines = text.split("\n")
    out: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= max_consecutive:
                out.append("")
        else:
            blank_run = 0
            out.append(line.rstrip())
    return "\n".join(out).strip()


def _drop_internal_marker_lines(text: str) -> str:
    kept: list[str] = []
    for line in text.split("\n"):
        lower = line.lower()
        if any(m.lower() in lower for m in _INTERNAL_LINE_MARKERS):
            continue
        kept.append(line)
    return "\n".join(kept)


# Model occasionally echoes fenced blocks; strip isolated ``` lines conservatively.
_FENCE_LINE_RE = re.compile(r"^\s*```\w*\s*$")


def _strip_fenced_line_noise(text: str) -> str:
    lines = [ln for ln in text.split("\n") if not _FENCE_LINE_RE.match(ln)]
    return "\n".join(lines)


def _soft_truncate_for_readability(text: str, soft: int) -> str:
    if soft < 200:
        soft = 200
    if len(text) <= soft:
        return text
    head = text[:soft]
    cut = head.rfind("\n\n")
    if cut > soft // 2:
        return head[:cut].rstrip() + "\n\n…"
    cut = head.rfind(". ")
    if cut > soft // 2:
        return head[: cut + 1].rstrip() + "\n\n…"
    return head.rstrip() + "…"


def format_telegram_bot_reply_text(
    text: str,
    *,
    soft_max_chars: int = TELEGRAM_REPLY_SOFT_MAX_CHARS,
) -> str:
    """
    Prepare assistant (or fallback) text for Telegram ``sendMessage`` without ``parse_mode``.

    Idempotent for already-clean short strings. Does not add internal metadata.
    """
    t = _normalize_newlines((text or "").strip())
    if not t:
        return ""
    t = _strip_disallowed_controls(t)
    t = _drop_internal_marker_lines(t)
    t = _strip_fenced_line_noise(t)
    t = _collapse_blank_lines(t)
    t = _soft_truncate_for_readability(t, soft_max_chars)
    return t.strip()


__all__ = [
    "TELEGRAM_REPLY_SOFT_MAX_CHARS",
    "format_telegram_bot_reply_text",
]
