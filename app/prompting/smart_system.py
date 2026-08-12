"""
In-process cached fragments of the system prompt (Layer 3 — static core).

``functools.lru_cache`` deduplicates repeated identity + tone work across thousands of
requests for the same bot configuration (SaaS hot path).
"""

from __future__ import annotations

import functools

from app.prompting.compact_tone import assemble_compact_tone_section
from app.prompting.style import assemble_warm_tone_section


@functools.lru_cache(maxsize=4096)
def cached_static_identity_and_compact_tone(
    bot_name: str,
    goal_type: str,
    niche_catalog_id: str,
    tone_key: str,
) -> str:
    """
    **Part A — static core (compact):** identity line + short tone block.

    ``tone_key`` uses the literal ``__none__`` when ``bot.tone`` is unset so the cache
    key stays hashable.
    """
    tone = None if tone_key == "__none__" else tone_key
    identity = (
        f'You are the conversational voice of «{bot_name}» for {goal_type} conversations '
        f'(niche catalog id `{niche_catalog_id}`). Sound human and specific to this role—not like a generic chatbot.'
    )
    return f"{identity}\n\n{assemble_compact_tone_section(tone)}"


@functools.lru_cache(maxsize=512)
def cached_full_warm_tone_block(tone_key: str) -> str:
    """Warm-tone markdown block keyed only by operator tone (large but repeated rarely per tone string)."""
    tone = None if tone_key == "__none__" else tone_key
    return assemble_warm_tone_section(tone)


def tone_cache_key(tone: str | None) -> str:
    return "__none__" if not (tone or "").strip() else (tone or "").strip()[:512]


__all__ = [
    "cached_full_warm_tone_block",
    "cached_static_identity_and_compact_tone",
    "tone_cache_key",
]
