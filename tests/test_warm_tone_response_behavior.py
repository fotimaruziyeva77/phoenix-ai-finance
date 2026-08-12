"""
Warm-tone **behavior** checks: prompt content (all niches) + heuristic evaluation of sample replies.

Live LLM calls are not required; golden samples document the target shape.
"""

from __future__ import annotations

import pytest
from app.prompting import PromptBuildInput, PromptBuildOptions, build_prompt_package
from app.prompting.compact_tone import COMPACT_TONE_TITLE
from app.prompting.style import WARM_TONE_SECTION_TITLE, assemble_warm_tone_section
from app.prompting.types import BotPromptSource
from app.prompting.warm_tone_evaluation import evaluate_warm_tone_response

from tests.warm_tone_sample_outputs import (
    SAMPLE_DEV_AGENCY_ACK_AND_ASK,
    SAMPLE_EDUCATION_ACK_AND_ASK,
    SAMPLE_EDUCATION_NO_NEW_QUESTION,
    SAMPLE_HEALTHCARE_ACK_AND_ASK,
    SAMPLE_ROBOTIC_VERBOSE_BAD,
    SAMPLE_SERVICES_ACK_AND_ASK,
)

NICHE_IDS = ("education", "healthcare", "dev_agency", "services")


def _bot(niche_id: str) -> BotPromptSource:
    return BotPromptSource(
        name=f"Bot-{niche_id}",
        niche_id=niche_id,
        goal_type="sales",
        tone="warm and professional",
        language="en",
        short_description=f"Intake for {niche_id}.",
    )


@pytest.mark.parametrize("niche_id", NICHE_IDS)
def test_system_prompt_includes_warm_tone_for_all_niches(niche_id: str) -> None:
    """Compact tone block is niche-agnostic and present regardless of catalog id."""
    inp = PromptBuildInput(bot=_bot(niche_id), user_message="Hello")
    pkg = build_prompt_package(inp)
    assert COMPACT_TONE_TITLE in pkg.system_prompt
    assert "one clear question" in pkg.system_prompt
    assert "generic AI boilerplate" in pkg.system_prompt
    assert "warm, concise" in pkg.system_prompt.lower()


@pytest.mark.parametrize("niche_id", NICHE_IDS)
def test_assembled_section_identical_across_niches(niche_id: str) -> None:
    """Same tone rules for every niche; only operator tone line varies with bot.tone."""
    b = _bot(niche_id)
    section = assemble_warm_tone_section(b.tone)
    assert "Stay concise" in section
    assert "Operator-configured tone hint" in section


def test_golden_education_sample_concise_one_question_polite() -> None:
    ok, viol = evaluate_warm_tone_response(
        SAMPLE_EDUCATION_ACK_AND_ASK,
        expect_at_least_one_question=True,
    )
    assert ok, viol
    assert "Thanks" in SAMPLE_EDUCATION_ACK_AND_ASK


def test_golden_healthcare_sample_concise_one_question() -> None:
    ok, viol = evaluate_warm_tone_response(
        SAMPLE_HEALTHCARE_ACK_AND_ASK,
        expect_at_least_one_question=True,
    )
    assert ok, viol


def test_golden_dev_agency_sample_concise_one_question() -> None:
    ok, viol = evaluate_warm_tone_response(
        SAMPLE_DEV_AGENCY_ACK_AND_ASK,
        expect_at_least_one_question=True,
    )
    assert ok, viol


def test_golden_services_sample_concise_one_question() -> None:
    ok, viol = evaluate_warm_tone_response(
        SAMPLE_SERVICES_ACK_AND_ASK,
        expect_at_least_one_question=True,
    )
    assert ok, viol


def test_education_sample_without_new_question_stays_concise() -> None:
    ok, viol = evaluate_warm_tone_response(
        SAMPLE_EDUCATION_NO_NEW_QUESTION,
        expect_at_least_one_question=False,
    )
    assert ok, viol


def test_robotic_verbose_multi_question_sample_fails_heuristics() -> None:
    ok, viol = evaluate_warm_tone_response(
        SAMPLE_ROBOTIC_VERBOSE_BAD,
        expect_at_least_one_question=False,
        max_chars=500,
    )
    assert not ok
    assert any("robotic_phrase" in v for v in viol)
    assert any("too_many_questions" in v or "too_long" in v for v in viol)


def test_checklist_dump_detected() -> None:
    bad = "Thanks.\n\n- What is your name?\n- What is your email?\n- Budget?"
    ok, viol = evaluate_warm_tone_response(bad, expect_at_least_one_question=False)
    assert not ok
    assert any(v.startswith("checklist_dump") for v in viol)


def test_prompt_instructs_concise_and_single_question() -> None:
    """Prompt-focused: instructions explicitly constrain verbosity and question count."""
    block = assemble_warm_tone_section(None)
    assert "concise" in block.lower() or "Concise" in block
    assert "one clear, useful question" in block
    assert "checklists" in block.lower() or "checklist" in block.lower()


def test_include_warm_tone_false_skips_style_for_each_niche() -> None:
    for niche_id in NICHE_IDS:
        inp = PromptBuildInput(
            bot=_bot(niche_id),
            user_message="Hi",
            options=PromptBuildOptions(include_warm_tone_guidance=False),
        )
        pkg = build_prompt_package(inp)
        assert WARM_TONE_SECTION_TITLE not in pkg.system_prompt
        assert COMPACT_TONE_TITLE not in pkg.system_prompt
