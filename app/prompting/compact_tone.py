"""Short fixed-size tone guidance (token-efficient alternative to full warm-tone block)."""

from __future__ import annotations

from app.prompting.style import operator_tone_addon

COMPACT_TONE_TITLE = "## Voice (required)"

_COMPACT_RULES = (
    "Be warm, concise, and professional; one short paragraph unless the user needs detail.",
    "No generic AI boilerplate; sound like this business. Ask one clear question at a time when you need info.",
)


def assemble_compact_tone_section(bot_tone: str | None) -> str:
    """
    Two-line tone block plus optional operator hint — replaces the long markdown list
    from :func:`~app.prompting.style.assemble_warm_tone_section` when saving input tokens.
    """
    lines = [COMPACT_TONE_TITLE, "\n".join(f"- {r}" for r in _COMPACT_RULES)]
    extra = operator_tone_addon(bot_tone)
    if extra:
        lines.append(f"- {extra}")
    return "\n".join(lines)


__all__ = ["COMPACT_TONE_TITLE", "assemble_compact_tone_section"]
