"""Defensive history shaping so the latest user turn is never duplicated in the prompt."""

from __future__ import annotations

from app.prompting.types import HistoryTurn


def clean_history_for_prompt(
    history: tuple[HistoryTurn, ...],
    current_user_message: str,
) -> tuple[HistoryTurn, ...]:
    """
    Drop trailing user turns that exactly match ``current_user_message``.

    Primary path loads history **before** persisting the latest user row, so duplicates
    should not occur; this keeps prompts safe if call order regresses or other writers
    append the same text twice.
    """
    cur = (current_user_message or "").strip()
    if not cur:
        return history
    h = list(history)
    while h and h[-1].role == "user" and (h[-1].content or "").strip() == cur:
        h.pop()
    return tuple(h)


__all__ = ["clean_history_for_prompt"]
