"""Deterministic question planner (one question at a time)."""

from __future__ import annotations

import pytest
from app.lib.niche_flow.dev_agency import DEV_AGENCY_CONVERSATION_FLOW
from app.lib.niche_flow.education import EDUCATION_CONVERSATION_FLOW
from app.lib.niche_flow.healthcare import HEALTHCARE_CONVERSATION_FLOW
from app.lib.niche_flow.schema import NicheConversationFlowDefinition
from app.lib.niche_flow.services import SERVICES_CONVERSATION_FLOW
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.services.question_planner import (
    QuestionPlannerAction,
    QuestionPlannerInput,
    QuestionPlannerResult,
    plan_next_question,
)

ALL_NICHE_FLOWS: tuple[tuple[str, NicheConversationFlowDefinition], ...] = (
    ("education", EDUCATION_CONVERSATION_FLOW),
    ("healthcare", HEALTHCARE_CONVERSATION_FLOW),
    ("dev_agency", DEV_AGENCY_CONVERSATION_FLOW),
    ("services", SERVICES_CONVERSATION_FLOW),
)


def _inp(
    *,
    flow: NicheConversationFlowDefinition,
    state: ConversationFlowState,
    data: dict[str, object] | None = None,
    intent: ConversationDetectedIntent = ConversationDetectedIntent.sales_interest,
    clar_round: int = 0,
    collect_optional: bool = True,
) -> QuestionPlannerInput:
    return QuestionPlannerInput(
        niche_flow=flow,
        current_state=state,
        collected_data=data,
        detected_intent=intent,
        clarification_round=clar_round,
        collect_optional_core_fields=collect_optional,
    )


def _assert_single_question_ux(text: str | None) -> None:
    """No multi-question dumps or paragraph stacks in suggested copy."""
    if text is None:
        return
    assert "\n\n" not in text, "avoid overwhelming paragraphs"
    assert text.count("?") <= 1, "at most one question per turn"


def _assert_asks_at_most_one_question(r: QuestionPlannerResult) -> None:
    if r.action in (
        QuestionPlannerAction.ask_core_field,
        QuestionPlannerAction.ask_clarification,
        QuestionPlannerAction.engage_opening,
    ):
        assert r.suggested_question_text is not None
        _assert_single_question_ux(r.suggested_question_text)
    elif r.action == QuestionPlannerAction.hold_no_question:
        assert r.suggested_question_text is None


def test_qualification_first_missing_required_single_question() -> None:
    r = plan_next_question(_inp(flow=EDUCATION_CONVERSATION_FLOW, state=ConversationFlowState.qualification, data={}))
    assert r.action == QuestionPlannerAction.ask_core_field
    assert r.target_field_key == "student_grade"
    assert r.suggested_question_text == EDUCATION_CONVERSATION_FLOW.qualification_question_examples[0]
    assert r.qualification_question_pool_index == 0
    assert r.suggest_set_qualification_complete is False
    _assert_asks_at_most_one_question(r)


def test_qualification_second_required_uses_aligned_example() -> None:
    # ``student_grade`` is the only required field; once it is present the planner (default
    # ``collect_optional=True``) moves on to the first OPTIONAL core field (``subject``), which
    # maps to qualification example index 1.
    r = plan_next_question(
        _inp(
            flow=EDUCATION_CONVERSATION_FLOW,
            state=ConversationFlowState.qualification,
            data={"student_grade": "Grade 9"},
        ),
    )
    assert r.target_field_key == "subject"
    assert r.suggested_question_text == EDUCATION_CONVERSATION_FLOW.qualification_question_examples[1]
    assert r.qualification_question_pool_index == 1
    # The single required field is filled, so qualification is structurally complete.
    assert r.suggest_set_qualification_complete is True
    _assert_asks_at_most_one_question(r)


def test_after_required_moves_to_optional_one_at_a_time() -> None:
    base = {"student_grade": "9", "subject": "Math"}
    r = plan_next_question(_inp(flow=EDUCATION_CONVERSATION_FLOW, state=ConversationFlowState.qualification, data=base))
    assert r.target_field_key == "lesson_format"
    assert r.suggest_set_qualification_complete is True
    # ``lesson_format`` is core-field index 2, but the qualification example pool now has only two
    # entries, so the per-field index clamps to the last example (index 1).
    assert r.suggested_question_text == EDUCATION_CONVERSATION_FLOW.qualification_question_examples[1]
    _assert_asks_at_most_one_question(r)


def test_skip_optional_when_disabled() -> None:
    base = {"student_grade": "9", "subject": "Math"}
    r = plan_next_question(
        QuestionPlannerInput(
            niche_flow=EDUCATION_CONVERSATION_FLOW,
            current_state=ConversationFlowState.qualification,
            collected_data=base,
            detected_intent=ConversationDetectedIntent.sales_interest,
            collect_optional_core_fields=False,
        ),
    )
    assert r.action == QuestionPlannerAction.hold_no_question
    assert r.suggested_question_text is None
    assert r.suggest_set_qualification_complete is True
    assert r.planner_reason_code == "qualification_core_complete"


def test_all_core_collected_hold() -> None:
    data = {
        "student_grade": "9",
        "subject": "Math",
        "lesson_format": "online",
        "branch_or_location": "NYC",
    }
    r = plan_next_question(_inp(flow=EDUCATION_CONVERSATION_FLOW, state=ConversationFlowState.qualification, data=data))
    assert r.action == QuestionPlannerAction.hold_no_question
    assert r.all_core_fields_collected is True
    assert r.suggest_set_qualification_complete is True


def test_clarification_one_question_per_round() -> None:
    # The clarification pool is now a single entry: round 0 asks it, round 1 is exhausted and the
    # planner holds (no repeat of the same question on the next round).
    pool = EDUCATION_CONVERSATION_FLOW.clarification_question_examples
    r0 = plan_next_question(_inp(flow=EDUCATION_CONVERSATION_FLOW, state=ConversationFlowState.clarification, clar_round=0))
    assert r0.action == QuestionPlannerAction.ask_clarification
    assert r0.suggested_question_text == pool[0]
    assert r0.clarification_pool_index == 0
    assert r0.next_clarification_round == 1
    _assert_asks_at_most_one_question(r0)
    r1 = plan_next_question(_inp(flow=EDUCATION_CONVERSATION_FLOW, state=ConversationFlowState.clarification, clar_round=1))
    assert r1.action == QuestionPlannerAction.hold_no_question
    assert r1.suggested_question_text is None
    assert r1.suggest_set_clarification_complete is True
    assert r1.suggested_question_text != r0.suggested_question_text
    _assert_asks_at_most_one_question(r1)


def test_clarification_exhausted_suggests_complete() -> None:
    n = len(EDUCATION_CONVERSATION_FLOW.clarification_question_examples)
    r = plan_next_question(_inp(flow=EDUCATION_CONVERSATION_FLOW, state=ConversationFlowState.clarification, clar_round=n))
    assert r.action == QuestionPlannerAction.hold_no_question
    assert r.suggest_set_clarification_complete is True
    assert r.planner_reason_code == "clarification_pool_exhausted"


def test_offer_phase_no_field_question() -> None:
    r = plan_next_question(
        _inp(flow=EDUCATION_CONVERSATION_FLOW, state=ConversationFlowState.offer, data={"student_grade": "x"}),
    )
    assert r.action == QuestionPlannerAction.hold_no_question
    assert r.suggested_question_text is None


def test_unknown_intent_start_uses_engage_opening() -> None:
    r = plan_next_question(
        _inp(
            flow=EDUCATION_CONVERSATION_FLOW,
            state=ConversationFlowState.start,
            data={},
            intent=ConversationDetectedIntent.unknown,
        ),
    )
    assert r.action == QuestionPlannerAction.engage_opening
    assert r.target_field_key == "student_grade"
    assert r.suggested_question_text is not None
    _assert_asks_at_most_one_question(r)


def test_sales_interest_start_asks_core_field() -> None:
    r = plan_next_question(
        _inp(
            flow=EDUCATION_CONVERSATION_FLOW,
            state=ConversationFlowState.start,
            data={},
            intent=ConversationDetectedIntent.sales_interest,
        ),
    )
    assert r.action == QuestionPlannerAction.ask_core_field


def test_completed_hold() -> None:
    r = plan_next_question(_inp(flow=EDUCATION_CONVERSATION_FLOW, state=ConversationFlowState.completed))
    assert r.action == QuestionPlannerAction.hold_no_question
    assert r.planner_reason_code == "terminal_completed"


# --- Cross-niche: one question, correct missing field, realistic progression ---


@pytest.mark.parametrize("niche_id,flow", ALL_NICHE_FLOWS)
def test_each_niche_first_question_targets_first_required_field(niche_id: str, flow: NicheConversationFlowDefinition) -> None:
    first_required = next(f for f in flow.core_fields if f.required_for_qualification)
    r = plan_next_question(_inp(flow=flow, state=ConversationFlowState.qualification, data={}))
    assert r.action == QuestionPlannerAction.ask_core_field
    assert r.target_field_key == first_required.key
    assert r.suggested_question_text == flow.qualification_question_examples[0]
    _assert_asks_at_most_one_question(r)


@pytest.mark.parametrize("niche_id,flow", ALL_NICHE_FLOWS)
def test_each_niche_qualification_examples_are_single_question_ux(niche_id: str, flow: NicheConversationFlowDefinition) -> None:
    for q in flow.qualification_question_examples:
        _assert_single_question_ux(q)
    for q in flow.clarification_question_examples:
        _assert_single_question_ux(q)


@pytest.mark.parametrize("niche_id,flow", ALL_NICHE_FLOWS)
def test_each_niche_progresses_missing_fields_in_order_no_repeat_on_filled(
    niche_id: str,
    flow: NicheConversationFlowDefinition,
) -> None:
    """Filling the current target must not re-ask that field; each step asks at most one question."""
    data: dict[str, object] = {}
    keys_asked: list[str] = []
    for _step in range(len(flow.core_fields) + 2):
        r = plan_next_question(_inp(flow=flow, state=ConversationFlowState.qualification, data=data))
        _assert_asks_at_most_one_question(r)
        if r.action == QuestionPlannerAction.hold_no_question:
            assert r.planner_reason_code == "qualification_core_complete"
            assert r.all_core_fields_collected is True
            break
        assert r.target_field_key is not None
        assert r.target_field_key not in data, f"{niche_id}: should not target already-collected {r.target_field_key}"
        keys_asked.append(r.target_field_key)
        # Realistic non-empty answer
        data = {**data, r.target_field_key: f"answer-for-{r.target_field_key}"}
    assert keys_asked == [f.key for f in flow.core_fields]


@pytest.mark.parametrize("niche_id,flow", ALL_NICHE_FLOWS)
def test_each_niche_idempotent_same_data_same_plan(niche_id: str, flow: NicheConversationFlowDefinition) -> None:
    data = {"x": "y"}  # irrelevant key
    for f in flow.core_fields:
        data[f.key] = f"val-{f.key}"
    r1 = plan_next_question(_inp(flow=flow, state=ConversationFlowState.qualification, data=data))
    r2 = plan_next_question(_inp(flow=flow, state=ConversationFlowState.qualification, data=data))
    assert r1 == r2


@pytest.mark.parametrize("niche_id,flow", ALL_NICHE_FLOWS)
def test_each_niche_clarification_advances_without_repeating_until_exhausted(
    niche_id: str,
    flow: NicheConversationFlowDefinition,
) -> None:
    pool = flow.clarification_question_examples
    seen: list[str] = []
    for i in range(len(pool)):
        r = plan_next_question(_inp(flow=flow, state=ConversationFlowState.clarification, clar_round=i))
        assert r.action == QuestionPlannerAction.ask_clarification
        assert r.suggested_question_text == pool[i]
        seen.append(r.suggested_question_text or "")
        _assert_asks_at_most_one_question(r)
    assert len(set(seen)) == len(pool)
    done = plan_next_question(_inp(flow=flow, state=ConversationFlowState.clarification, clar_round=len(pool)))
    assert done.suggested_question_text is None
    assert done.suggest_set_clarification_complete is True


# --- Realistic partial snapshots per niche ---


def test_healthcare_realistic_partial_then_next_field() -> None:
    flow = HEALTHCARE_CONVERSATION_FLOW
    r1 = plan_next_question(
        _inp(
            flow=flow,
            state=ConversationFlowState.qualification,
            data={"specialty": "Pediatrics"},
        ),
    )
    assert r1.target_field_key == "appointment_type"
    assert "first visit" in (r1.suggested_question_text or "").lower() or "follow-up" in (
        r1.suggested_question_text or ""
    ).lower()
    r2 = plan_next_question(
        _inp(
            flow=flow,
            state=ConversationFlowState.qualification,
            data={"specialty": "Pediatrics", "appointment_type": "follow-up cleaning"},
        ),
    )
    assert r2.target_field_key == "preferred_time"
    assert r2.suggest_set_qualification_complete is True
    _assert_asks_at_most_one_question(r2)


def test_dev_agency_realistic_partial_then_next_field() -> None:
    flow = DEV_AGENCY_CONVERSATION_FLOW
    r1 = plan_next_question(
        _inp(
            flow=flow,
            state=ConversationFlowState.qualification,
            data={"requested_solution": "Automate lead capture from Instagram"},
        ),
    )
    assert r1.target_field_key == "website_or_bot_or_crm"
    assert "chatbot" in (r1.suggested_question_text or "").lower() or "website" in (r1.suggested_question_text or "").lower()
    _assert_asks_at_most_one_question(r1)


def test_services_realistic_partial_then_next_field() -> None:
    flow = SERVICES_CONVERSATION_FLOW
    r1 = plan_next_question(
        _inp(
            flow=flow,
            state=ConversationFlowState.qualification,
            data={"service_type": "Emergency pipe leak under kitchen sink"},
        ),
    )
    # ``service_type`` is the only required field; the next core field is the optional ``location``.
    # Its per-field example index (1) clamps to the last entry in the now-shorter qualification pool.
    assert r1.target_field_key == "location"
    assert r1.suggested_question_text == flow.qualification_question_examples[1]
    _assert_asks_at_most_one_question(r1)


def test_education_realistic_partial_timeline_question_still_single() -> None:
    flow = EDUCATION_CONVERSATION_FLOW
    r = plan_next_question(
        _inp(
            flow=flow,
            state=ConversationFlowState.qualification,
            data={
                "student_grade": "Grade 11",
                "subject": "IB Physics",
                "lesson_format": "hybrid",
            },
        ),
    )
    assert r.target_field_key == "branch_or_location"
    # ``branch_or_location`` is core-field index 3, but the qualification pool now has only two
    # entries, so the per-field example index clamps to the last one (index 1).
    assert r.suggested_question_text == flow.qualification_question_examples[1]
    _assert_asks_at_most_one_question(r)


# --- Toward offer / closing ---


def test_when_required_complete_planner_signals_qualification_complete_for_state_machine() -> None:
    """Orchestrator can set qualification_complete and transition toward offer."""
    flow = SERVICES_CONVERSATION_FLOW
    data = {"service_type": "HVAC tune-up", "location": "Austin, TX"}
    r = plan_next_question(_inp(flow=flow, state=ConversationFlowState.qualification, data=data))
    assert r.suggest_set_qualification_complete is True
    assert r.target_field_key == "urgency"


def test_offer_phase_suggest_qualification_complete_when_data_already_complete() -> None:
    flow = EDUCATION_CONVERSATION_FLOW
    data = {f.key: "ok" for f in flow.core_fields}
    r = plan_next_question(_inp(flow=flow, state=ConversationFlowState.offer, data=data))
    assert r.action == QuestionPlannerAction.hold_no_question
    assert r.suggest_set_qualification_complete is True
    assert r.all_core_fields_collected is True


def test_closing_phase_hold_no_extra_field_question_but_flags_reflect_data() -> None:
    flow = HEALTHCARE_CONVERSATION_FLOW
    data = {f.key: "filled" for f in flow.core_fields}
    r = plan_next_question(_inp(flow=flow, state=ConversationFlowState.closing, data=data))
    assert r.action == QuestionPlannerAction.hold_no_question
    assert r.suggested_question_text is None
    assert r.suggest_set_qualification_complete is True
    assert r.all_core_fields_collected is True


def test_objection_handling_does_not_dump_qualification_questions() -> None:
    flow = DEV_AGENCY_CONVERSATION_FLOW
    r = plan_next_question(_inp(flow=flow, state=ConversationFlowState.objection_handling, data={}))
    assert r.action == QuestionPlannerAction.hold_no_question
    assert r.suggested_question_text is None
