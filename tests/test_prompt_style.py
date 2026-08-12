"""Warm-tone style layer for system prompts."""

from __future__ import annotations

from app.prompting import PromptBuildInput, PromptBuildOptions, build_prompt_package
from app.prompting.compact_tone import COMPACT_TONE_TITLE
from app.prompting.style import WARM_TONE_SECTION_TITLE, assemble_warm_tone_section, operator_tone_addon
from app.prompting.types import BotPromptSource


def _bot(*, tone: str | None = "friendly and clear") -> BotPromptSource:
    return BotPromptSource(
        name="Acme Tutor",
        niche_id="education",
        goal_type="sales",
        welcome_message="Hi!",
        tone=tone,
        language="en",
        short_description="Tutoring intake.",
    )


def test_assemble_warm_tone_section_includes_core_rules() -> None:
    s = assemble_warm_tone_section(None)
    assert WARM_TONE_SECTION_TITLE in s
    assert "one clear, useful question" in s
    assert "manipulative" in s
    assert "generic AI boilerplate" in s or "AI" in s


def test_operator_tone_addon_optional() -> None:
    assert operator_tone_addon(None) is None
    assert operator_tone_addon("   ") is None
    assert "friendly" in (operator_tone_addon("friendly") or "")


def test_warm_tone_in_system_prompt_by_default() -> None:
    inp = PromptBuildInput(bot=_bot(), user_message="Hello")
    pkg = build_prompt_package(inp)
    assert COMPACT_TONE_TITLE in pkg.system_prompt
    assert "Operator-configured tone hint" in pkg.system_prompt
    assert "friendly and clear" in pkg.system_prompt


def test_identity_avoids_generic_ai_assistant_phrase() -> None:
    inp = PromptBuildInput(bot=_bot(), user_message="Hi")
    pkg = build_prompt_package(inp)
    assert "an AI assistant" not in pkg.system_prompt.lower()
    assert "conversational voice" in pkg.system_prompt


def test_full_warm_tone_when_compact_disabled() -> None:
    inp = PromptBuildInput(
        bot=_bot(),
        user_message="Hello",
        options=PromptBuildOptions(use_compact_tone=False),
    )
    pkg = build_prompt_package(inp)
    assert WARM_TONE_SECTION_TITLE in pkg.system_prompt


def test_include_warm_tone_false_omits_style_block() -> None:
    inp = PromptBuildInput(
        bot=_bot(),
        user_message="Hi",
        options=PromptBuildOptions(include_warm_tone_guidance=False),
    )
    pkg = build_prompt_package(inp)
    assert WARM_TONE_SECTION_TITLE not in pkg.system_prompt
    assert "Operator-configured tone hint" not in pkg.system_prompt


def test_no_bot_tone_skips_operator_line() -> None:
    inp = PromptBuildInput(
        bot=BotPromptSource(name="X", niche_id="services", goal_type="support", tone=None),
        user_message="Hi",
    )
    pkg = build_prompt_package(inp)
    assert COMPACT_TONE_TITLE in pkg.system_prompt
    assert "Operator-configured tone hint" not in pkg.system_prompt
