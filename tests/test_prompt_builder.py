"""Prompt package assembly (bounded history, scrubbing, overrides)."""

from __future__ import annotations

from app.prompting import (
    HistoryTurn,
    PromptBuildInput,
    PromptBuildOptions,
    PromptExtensionContext,
    build_prompt_package,
    scrub_secrets_for_prompt,
)
from app.prompting.history import truncate_history_turns
from app.prompting.types import BotPromptSource


def _bot() -> BotPromptSource:
    return BotPromptSource(
        name="Test Bot",
        niche_id="education",
        goal_type="support",
        welcome_message="Hi there!",
        tone="friendly",
        language="en",
        short_description="Helps learners.",
    )


def test_build_prompt_package_structure_and_provider_messages() -> None:
    inp = PromptBuildInput(
        bot=_bot(),
        user_message="What courses?",
        history=(
            HistoryTurn(role="user", content="Hello"),
            HistoryTurn(role="assistant", content="Hi! How can I help?"),
        ),
    )
    pkg = build_prompt_package(inp)
    assert "Test Bot" in pkg.system_prompt
    assert "education" in pkg.system_prompt
    assert len(pkg.history_messages) == 2
    assert pkg.history_messages[0].role == "user"
    assert pkg.current_user_message == "What courses?"
    msgs = pkg.as_provider_messages()
    assert msgs[0].role == "system"
    assert msgs[-1].role == "user"
    assert msgs[-1].content == "What courses?"


def test_history_truncated_by_message_count() -> None:
    long_h = tuple(HistoryTurn(role="user", content=f"m{i}") for i in range(30))
    inp = PromptBuildInput(
        bot=_bot(),
        user_message="last",
        history=long_h,
        options=PromptBuildOptions(max_history_messages=5),
    )
    pkg = build_prompt_package(inp)
    assert len(pkg.history_messages) == 5
    assert pkg.history_messages[-1].content == "m29"


def test_history_truncated_by_total_chars() -> None:
    h = (
        HistoryTurn(role="user", content="x" * 100),
        HistoryTurn(role="assistant", content="y" * 100),
        HistoryTurn(role="user", content="z" * 100),
    )
    opts = PromptBuildOptions(
        max_history_messages=10,
        max_chars_per_message=200,
        max_total_history_chars=120,
    )
    out = truncate_history_turns(h, opts)
    total = sum(len(t.content) for t in out)
    assert total <= 120
    assert len(out) >= 1


def test_system_override_replaces_assembly_when_allowed() -> None:
    inp = PromptBuildInput(
        bot=_bot(),
        user_message="Hi",
        system_prompt_override="Custom system only.",
        options=PromptBuildOptions(allow_system_prompt_override=True),
    )
    pkg = build_prompt_package(inp)
    assert pkg.system_prompt == "Custom system only."
    assert "Test Bot" not in pkg.system_prompt


def test_system_override_ignored_when_disallowed() -> None:
    inp = PromptBuildInput(
        bot=_bot(),
        user_message="Hi",
        system_prompt_override="IGNORED",
        options=PromptBuildOptions(allow_system_prompt_override=False),
    )
    pkg = build_prompt_package(inp)
    assert "IGNORED" not in pkg.system_prompt
    assert "Test Bot" in pkg.system_prompt


def test_extension_context_appended_to_system() -> None:
    ext = PromptExtensionContext(
        niche_script_excerpt="Ask for grade level.",
        knowledge_excerpt="PDF page 1 says …",
        lead_flow_hint="User is warm lead.",
    )
    inp = PromptBuildInput(bot=_bot(), user_message="Q", extensions=ext)
    pkg = build_prompt_package(inp)
    assert "Niche script (excerpt): Ask for grade level." in pkg.system_prompt
    # Knowledge block is appended as the formatted excerpt itself (see PromptExtensionContext).
    assert "PDF page 1 says" in pkg.system_prompt
    assert "Lead flow hint:" in pkg.system_prompt


def test_scrub_secrets_in_user_history_and_system() -> None:
    leaked = "AIzaSy0123456789012345678901234567890AB"
    inp = PromptBuildInput(
        bot=_bot(),
        user_message=f"use {leaked} please",
        history=(HistoryTurn(role="user", content=leaked),),
    )
    pkg = build_prompt_package(inp)
    assert leaked not in pkg.current_user_message
    assert "[REDACTED]" in pkg.current_user_message
    assert leaked not in pkg.history_messages[0].content


def test_niche_context_override_wins_over_registry() -> None:
    inp = PromptBuildInput(
        bot=_bot(),
        user_message="x",
        niche_context="Custom niche paragraph from caller.",
    )
    pkg = build_prompt_package(inp)
    assert "Custom niche paragraph" in pkg.system_prompt


def test_scrub_secrets_for_prompt_standalone() -> None:
    assert "AIzaSy" not in scrub_secrets_for_prompt("key AIzaSy0123456789012345678901234567890AB")
