"""Tests for :mod:`app.prompting.engagement_rules`."""

from __future__ import annotations

import pytest

from app.prompting.engagement_rules import engagement_rules_for_goal_type


@pytest.mark.parametrize("goal_type", ("sales", "consulting", "support", "faq"))
def test_all_goal_types_produce_non_empty_output(goal_type: str) -> None:
    result = engagement_rules_for_goal_type(goal_type)
    assert result
    assert len(result) > 100


@pytest.mark.parametrize("goal_type", ("sales", "consulting", "support", "faq"))
def test_all_goal_types_include_off_topic_guardrail(goal_type: str) -> None:
    result = engagement_rules_for_goal_type(goal_type)
    assert "Staying on topic" in result
    assert "off-topic" in result.lower()


def test_sales_includes_lead_capture_flow() -> None:
    result = engagement_rules_for_goal_type("sales")
    assert "phone capture" in result
    assert "greet warmly" in result
    assert "friendly, efficient sales assistant" in result


def test_consulting_includes_diagnosis_and_capture() -> None:
    result = engagement_rules_for_goal_type("consulting")
    assert "phone capture" in result
    assert "diagnostic question" in result
    assert "consulting assistant" in result


def test_support_includes_escalation() -> None:
    result = engagement_rules_for_goal_type("support")
    assert "Escalate when needed" in result
    assert "human operator" in result
    assert "support assistant" in result


def test_faq_includes_escalation() -> None:
    result = engagement_rules_for_goal_type("faq")
    assert "Escalate unknowns" in result
    assert "human representative" in result
    assert "FAQ assistant" in result


def test_unknown_goal_type_gets_off_topic_only() -> None:
    result = engagement_rules_for_goal_type("unknown_type")
    assert "Staying on topic" in result
    assert "Conversation strategy" not in result


def test_empty_and_none_goal_type_handled() -> None:
    assert engagement_rules_for_goal_type("")
    assert engagement_rules_for_goal_type("  ")


def test_case_insensitive_goal_type() -> None:
    upper = engagement_rules_for_goal_type("SALES")
    lower = engagement_rules_for_goal_type("sales")
    assert upper == lower


def test_prompt_builder_includes_engagement_rules() -> None:
    """Verify the builder actually injects engagement rules into the system prompt."""
    from app.prompting.builder import build_prompt_package
    from app.prompting.types import BotPromptSource, PromptBuildInput

    bot = BotPromptSource(
        name="TestBot",
        niche_id="generic",
        goal_type="sales",
        language="en",
    )
    inp = PromptBuildInput(bot=bot, user_message="Hello")
    pkg = build_prompt_package(inp)
    assert "Conversation strategy" in pkg.system_prompt
    assert "Staying on topic" in pkg.system_prompt
    assert "phone capture" in pkg.system_prompt


def test_prompt_builder_support_bot_has_escalation() -> None:
    from app.prompting.builder import build_prompt_package
    from app.prompting.types import BotPromptSource, PromptBuildInput

    bot = BotPromptSource(
        name="SupportBot",
        niche_id="generic",
        goal_type="support",
        language="en",
    )
    inp = PromptBuildInput(bot=bot, user_message="I need help")
    pkg = build_prompt_package(inp)
    assert "Escalate when needed" in pkg.system_prompt
    assert "human operator" in pkg.system_prompt
    assert "Staying on topic" in pkg.system_prompt
