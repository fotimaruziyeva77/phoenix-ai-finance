"""
Warm, professional **response style** guidance for system prompts.

Niche-agnostic rules the model must follow so replies stay human, concise, and
trustworthy. Operator ``bot.tone`` is blended as a light hint, not a personality
overlay—see :func:`assemble_warm_tone_section`.
"""

from __future__ import annotations

WARM_TONE_SECTION_TITLE = "## How to write (required)"

# Short lines: easy for the model to scan; no essay.
_WARM_TONE_RULE_LINES: tuple[str, ...] = (
    "Be warm, calm, and professional—like a capable colleague, not a script or a cheerleader.",
    "Stay concise: usually one short paragraph; avoid walls of text and long preambles.",
    "If the user said something specific, acknowledge it in one brief phrase before you continue.",
    "When you need information, ask one clear, useful question at a time—no question stacks or robotic checklists.",
    "Guide the conversation helpfully toward clarity or a sensible next step; never pressure, invent urgency, or use manipulative language.",
    'Do not use generic AI boilerplate (“As an AI…”, “I’m an AI assistant…”). Write as this business’s voice.',
    "Keep the tone premium and trustworthy: no hype, cheesy flattery, or exaggerated emotion.",
    "Do not add emojis unless they clearly fit the brand; default to none.",
)


def _rules_body() -> str:
    return "\n".join(f"- {line}" for line in _WARM_TONE_RULE_LINES)


def operator_tone_addon(bot_tone: str | None) -> str | None:
    """
    Optional line derived from bot config.

    Intentionally understated so operators can steer style slightly without turning
    the model into a caricature.
    """
    t = (bot_tone or "").strip()
    if not t:
        return None
    return (
        "Operator-configured tone hint (blend subtly; stay natural—do not sound performative): "
        f"{t}"
    )


def assemble_warm_tone_section(bot_tone: str | None) -> str:
    """
    Full markdown-style block injected into the system prompt (all niches).

    ``bot_tone`` is appended as a single optional line when present.
    """
    chunks: list[str] = [WARM_TONE_SECTION_TITLE, _rules_body()]
    extra = operator_tone_addon(bot_tone)
    if extra:
        chunks.append(f"- {extra}")
    return "\n".join(chunks)


__all__ = [
    "WARM_TONE_SECTION_TITLE",
    "assemble_warm_tone_section",
    "operator_tone_addon",
]
