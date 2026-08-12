"""Heuristics for when sales intent may call Gemini (rules missed)."""

from __future__ import annotations

import re

_AMBIGUITY_MARKERS = re.compile(
    r"\b("
    r"not\s+sure|unsure|maybe|perhaps|either\s+or|confused|don't\s+know|do\s+not\s+know|"
    r"nimadir|bilmayman|tushunmadim"
    r")\b",
    re.IGNORECASE,
)


def sales_intent_message_ambiguous_for_gemini(text: str) -> bool:
    """
    When rules miss, treat long / hedge-heavy utterances as ambiguous (Gemini allowed).

    Short, plain lines defer to ``sales_default`` when ambiguity-only mode is on.
    """
    raw = (text or "").strip()
    if not raw:
        return False
    if len(raw) > 140:
        return True
    words = raw.split()
    if len(words) >= 9:
        return True
    if len(words) >= 4 and _AMBIGUITY_MARKERS.search(raw):
        return True
    if "?" in raw and len(words) >= 6:
        return True
    return False


__all__ = ["sales_intent_message_ambiguous_for_gemini"]
