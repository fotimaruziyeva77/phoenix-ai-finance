"""Prompt sizing policy for short user turns (token / latency efficiency)."""

from __future__ import annotations

import dataclasses

from app.core.config import Settings
from app.prompting.types import PromptBuildOptions


def prompt_build_options_for_user_text(
    settings: Settings,
    user_text: str,
    *,
    knowledge_injected: bool = False,
) -> PromptBuildOptions:
    """
    When the user message is very short, tighten history budgets and enable ``slim_system_prompt``
    in :func:`~app.prompting.builder.build_prompt_package`.
    """
    base = PromptBuildOptions()
    if knowledge_injected:
        return base
    if not settings.ai_prompt_slim_for_short_messages:
        return base
    t = (user_text or "").strip()
    if not t or len(t.split()) >= int(settings.ai_prompt_slim_word_threshold):
        return base
    cap = max(1, int(settings.ai_prompt_slim_history_cap))
    return dataclasses.replace(
        base,
        slim_system_prompt=True,
        max_history_messages=min(base.max_history_messages, cap),
        max_total_history_chars=min(base.max_total_history_chars, 6000),
        max_chars_per_message=min(base.max_chars_per_message, 512),
    )


__all__ = ["prompt_build_options_for_user_text"]
