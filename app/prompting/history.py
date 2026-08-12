"""Bounded conversation history for prompts."""

from __future__ import annotations

from app.prompting.types import HistoryTurn, PromptBuildOptions

# Hard upper bound on total history characters regardless of PromptBuildOptions.
# Prevents accidental token bloat when callers pass a permissive options object.
_MAX_HISTORY_CHARS_HARD_CAP: int = 12_000


def truncate_history_turns(
    history: tuple[HistoryTurn, ...],
    options: PromptBuildOptions,
) -> tuple[HistoryTurn, ...]:
    """
    Keep the most recent turns under ``max_history_messages`` and character budgets.

    Drops oldest messages first. Per-message cap applied before counting totals.

    The total character budget is the *lesser* of ``options.max_total_history_chars``
    and ``_MAX_HISTORY_CHARS_HARD_CAP`` (12 000) so that callers with a permissive
    options object never inflate context unexpectedly.
    """
    max_msgs = max(0, options.max_history_messages)
    max_per = max(1, options.max_chars_per_message)
    # Enforce hard cap: never exceed 12 000 chars regardless of options.
    max_total = min(max(0, options.max_total_history_chars), _MAX_HISTORY_CHARS_HARD_CAP)

    trimmed: list[HistoryTurn] = []
    for turn in history:
        content = turn.content
        if len(content) > max_per:
            content = content[: max_per - 3] + "..."
        trimmed.append(HistoryTurn(role=turn.role, content=content))

    # Take suffix of at most max_msgs messages
    window = trimmed[-max_msgs:] if max_msgs else []

    # Enforce total char budget (content only) from the end
    acc = 0
    kept: list[HistoryTurn] = []
    for turn in reversed(window):
        ln = len(turn.content)
        if acc + ln > max_total:
            break
        kept.append(turn)
        acc += ln
    return tuple(reversed(kept))
