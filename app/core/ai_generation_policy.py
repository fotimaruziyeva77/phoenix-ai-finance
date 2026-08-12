"""MVP caps for LLM generation (output tokens); shared by chat, sales orchestrator, and classifiers."""

from __future__ import annotations


def resolve_max_output_tokens(
    *,
    bot_max_output_tokens: int | None,
    ceiling: int,
    default_when_unset: int,
    floor: int = 256,
) -> int:
    """
    Pick a bounded ``max_output_tokens`` for provider calls.

    * Per-bot value (when set) is clamped to ``ceiling`` and at least ``floor``.
    * When unset, use ``default_when_unset`` (then clamp the same way).
    """
    ceiling = max(int(ceiling), int(floor))
    raw = default_when_unset if bot_max_output_tokens is None else int(bot_max_output_tokens)
    if raw < floor:
        raw = floor
    return min(raw, ceiling)


def clamp_small_completion_budget(requested: int, ceiling: int, floor: int = 32) -> int:
    """For tiny completions (e.g. intent labels), clamp to ``[floor, min(requested, ceiling)]``."""
    c = max(int(ceiling), int(floor))
    r = max(int(requested), int(floor))
    return min(r, c)
