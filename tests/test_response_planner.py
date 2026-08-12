"""Response planning layer (modes + structured strategy, no NLG)."""

from __future__ import annotations

import json

import pytest
from app.lib.niche_flow.education import EDUCATION_CONVERSATION_FLOW
from app.lib.niche_flow.healthcare import HEALTHCARE_CONVERSATION_FLOW
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.services.question_planner import QuestionPlannerAction, QuestionPlannerResult
from app.services.response_planner import (
    PromptBuilderContextSlice,
    ResponseMode,
    ResponsePlannerInput,
    ResponseStrategy,
    plan_response_strategy,
)

_EXPECTED_MODES: frozenset[str] = frozenset(m.value for m in ResponseMode)


def _qp(
    *,
    action: QuestionPlannerAction = QuestionPlannerAction.ask_core_field,
    suggested: str | None = "What subject?",
    reason: str = "qualification_ask_one_core_field",
    state: ConversationFlowState = ConversationFlowState.qualification,
    intent: ConversationDetectedIntent = ConversationDetectedIntent.sales_interest,
    hold: bool = False,
    qual_complete: bool = False,
    all_core: bool = False,
    target: str | None = "subject",
    desc: str | None = "Subject",
) -> QuestionPlannerResult:
    if hold:
        return QuestionPlannerResult(
            action=QuestionPlannerAction.hold_no_question,
            target_field_key=None,
            suggested_question_text=None,
            field_spec_description=None,
            qualification_question_pool_index=None,
            clarification_pool_index=None,
            suggest_set_qualification_complete=qual_complete,
            all_core_fields_collected=all_core,
            suggest_set_clarification_complete=False,
            planner_reason_code=reason,
            effective_state=state,
            effective_intent=intent,
            next_clarification_round=0,
        )
    return QuestionPlannerResult(
        action=action,
        target_field_key=target,
        suggested_question_text=suggested,
        field_spec_description=desc,
        qualification_question_pool_index=0,
        clarification_pool_index=None,
        suggest_set_qualification_complete=qual_complete,
        all_core_fields_collected=all_core,
        suggest_set_clarification_complete=False,
        planner_reason_code=reason,
        effective_state=state,
        effective_intent=intent,
        next_clarification_round=0,
    )


def _plan(
    *,
    state: ConversationFlowState,
    intent: ConversationDetectedIntent,
    qp: QuestionPlannerResult,
) -> ResponseStrategy:
    return plan_response_strategy(
        ResponsePlannerInput(
            niche_flow=EDUCATION_CONVERSATION_FLOW,
            current_state=state,
            detected_intent=intent,
            question_plan=qp,
            collected_data={},
        ),
    )


def test_mode_offer_locked_to_state() -> None:
    r = _plan(
        state=ConversationFlowState.offer,
        intent=ConversationDetectedIntent.sales_interest,
        qp=_qp(hold=True, state=ConversationFlowState.offer, reason="phase_offer_no_field_question"),
    )
    assert r.response_mode is ResponseMode.offer
    assert r.next_question is None
    assert len(r.key_talking_points) >= 1
    assert r.prompt_builder_context.conversation_phase == "offer"


def test_mode_objection_and_closing() -> None:
    ro = _plan(
        state=ConversationFlowState.objection_handling,
        intent=ConversationDetectedIntent.support,
        qp=_qp(hold=True, state=ConversationFlowState.objection_handling, reason="phase_objection_handling_no_field_question"),
    )
    assert ro.response_mode is ResponseMode.handle_objection
    rc = _plan(
        state=ConversationFlowState.closing,
        intent=ConversationDetectedIntent.sales_interest,
        qp=_qp(hold=True, state=ConversationFlowState.closing, reason="phase_closing_no_field_question"),
    )
    assert rc.response_mode is ResponseMode.closing_prompt


def test_mode_completed_and_fallback() -> None:
    r = _plan(
        state=ConversationFlowState.completed,
        intent=ConversationDetectedIntent.greeting,
        qp=_qp(hold=True, state=ConversationFlowState.completed, reason="terminal_completed"),
    )
    assert r.response_mode is ResponseMode.fallback_response
    rf = _plan(
        state=ConversationFlowState.fallback,
        intent=ConversationDetectedIntent.unknown,
        qp=_qp(
            hold=True,
            state=ConversationFlowState.fallback,
            reason="start_intent_unknown",
            suggested=None,
        ),
    )
    assert rf.response_mode is ResponseMode.fallback_response


def test_greet_at_start_with_greeting_intent() -> None:
    r = _plan(
        state=ConversationFlowState.start,
        intent=ConversationDetectedIntent.greeting,
        qp=_qp(
            state=ConversationFlowState.start,
            intent=ConversationDetectedIntent.greeting,
            suggested="Which grade?",
            target="student_grade",
        ),
    )
    assert r.response_mode is ResponseMode.greet
    assert r.next_question == "Which grade?"
    assert "warm" in r.tone_hints


def test_engage_opening_is_ask_question_mode() -> None:
    r = _plan(
        state=ConversationFlowState.start,
        intent=ConversationDetectedIntent.unknown,
        qp=_qp(
            action=QuestionPlannerAction.engage_opening,
            state=ConversationFlowState.start,
            intent=ConversationDetectedIntent.unknown,
            suggested="Which grade?",
        ),
    )
    assert r.response_mode is ResponseMode.ask_question


def test_substantive_intent_gets_acknowledge_and_ask() -> None:
    r = _plan(
        state=ConversationFlowState.qualification,
        intent=ConversationDetectedIntent.sales_interest,
        qp=_qp(suggested="One thing?"),
    )
    assert r.response_mode is ResponseMode.acknowledge_and_ask
    assert r.next_question == "One thing?"
    assert "brief_acknowledgment" in r.tone_hints


def test_unknown_intent_gets_ask_question() -> None:
    r = _plan(
        state=ConversationFlowState.qualification,
        intent=ConversationDetectedIntent.unknown,
        qp=_qp(suggested="One thing?"),
    )
    assert r.response_mode is ResponseMode.ask_question


def test_qualification_complete_hold_bridges_without_next_question() -> None:
    r = _plan(
        state=ConversationFlowState.qualification,
        intent=ConversationDetectedIntent.sales_interest,
        qp=_qp(
            hold=True,
            reason="qualification_core_complete",
            qual_complete=True,
            all_core=True,
        ),
    )
    assert r.response_mode is ResponseMode.acknowledge_and_ask
    assert r.next_question is None
    assert any("Core details" in p or "fit" in p for p in r.key_talking_points)


def test_clarification_question_modes() -> None:
    r_direct = _plan(
        state=ConversationFlowState.clarification,
        intent=ConversationDetectedIntent.unknown,
        qp=_qp(
            action=QuestionPlannerAction.ask_clarification,
            state=ConversationFlowState.clarification,
            intent=ConversationDetectedIntent.unknown,
            suggested="Clarify X?",
            target=None,
            desc=None,
        ),
    )
    assert r_direct.response_mode is ResponseMode.ask_question
    r_ack = _plan(
        state=ConversationFlowState.clarification,
        intent=ConversationDetectedIntent.consulting,
        qp=_qp(
            action=QuestionPlannerAction.ask_clarification,
            state=ConversationFlowState.clarification,
            intent=ConversationDetectedIntent.consulting,
            suggested="Clarify X?",
            target=None,
            desc=None,
        ),
    )
    assert r_ack.response_mode is ResponseMode.acknowledge_and_ask


def test_prompt_builder_context_matches_strategy() -> None:
    qp = _qp(suggested="Q?", target="student_grade")
    r = plan_response_strategy(
        ResponsePlannerInput(
            niche_flow=EDUCATION_CONVERSATION_FLOW,
            current_state=ConversationFlowState.qualification,
            detected_intent=ConversationDetectedIntent.faq,
            question_plan=qp,
            collected_data=None,
        ),
    )
    ctx = r.prompt_builder_context
    assert ctx.niche_id == "education"
    assert ctx.response_mode == r.response_mode.value
    assert ctx.target_field_key == "student_grade"
    assert ctx.planner_action == qp.action.value


def test_strategy_is_not_final_nl_body() -> None:
    r = _plan(
        state=ConversationFlowState.offer,
        intent=ConversationDetectedIntent.sales_interest,
        qp=_qp(hold=True, state=ConversationFlowState.offer, reason="phase_offer_no_field_question"),
    )
    assert not hasattr(r, "assistant_message")
    assert isinstance(r.key_talking_points, tuple)


# --- Explicit mode coverage (checklist) ---


def test_greeting_mode_stable_value_tones_and_qualification_points() -> None:
    r = _plan(
        state=ConversationFlowState.start,
        intent=ConversationDetectedIntent.greeting,
        qp=_qp(
            state=ConversationFlowState.start,
            intent=ConversationDetectedIntent.greeting,
            suggested="Hi — what grade?",
            target="student_grade",
        ),
    )
    assert r.response_mode is ResponseMode.greet
    assert r.response_mode.value == "greet"
    assert r.strategy_reason_code == "start_greeting"
    assert r.tone_hints == ("warm", "brief", "welcoming")
    assert r.key_talking_points == EDUCATION_CONVERSATION_FLOW.qualification_goals[:2]
    assert r.next_question == "Hi — what grade?"
    assert r.prompt_builder_context.response_mode == "greet"


def test_greeting_mode_coerces_string_start_state() -> None:
    r = plan_response_strategy(
        ResponsePlannerInput(
            niche_flow=EDUCATION_CONVERSATION_FLOW,
            current_state="start",
            detected_intent="greeting",
            question_plan=_qp(
                state=ConversationFlowState.start,
                intent=ConversationDetectedIntent.greeting,
                suggested="Q?",
            ),
        ),
    )
    assert r.response_mode is ResponseMode.greet


def test_ask_question_mode_qualification_unknown_intent() -> None:
    r = _plan(
        state=ConversationFlowState.qualification,
        intent=ConversationDetectedIntent.unknown,
        qp=_qp(suggested="What subject are you focusing on?"),
    )
    assert r.response_mode is ResponseMode.ask_question
    assert r.response_mode.value == "ask_question"
    assert r.strategy_reason_code == "question_direct"
    assert r.tone_hints == ("curious", "single_question", "not_overwhelming")
    assert r.next_question == "What subject are you focusing on?"


def test_ask_question_mode_engage_opening() -> None:
    # ``fallback`` state is handled before ``engage_opening``; use qualification so opening path runs.
    r = _plan(
        state=ConversationFlowState.qualification,
        intent=ConversationDetectedIntent.unknown,
        qp=_qp(
            action=QuestionPlannerAction.engage_opening,
            state=ConversationFlowState.qualification,
            intent=ConversationDetectedIntent.unknown,
            suggested="What brings you here today?",
        ),
    )
    assert r.response_mode is ResponseMode.ask_question
    assert r.strategy_reason_code == "planner_engage_opening"


def test_offer_mode_uses_niche_offer_framing_no_next_question() -> None:
    r = _plan(
        state=ConversationFlowState.offer,
        intent=ConversationDetectedIntent.consulting,
        qp=_qp(hold=True, state=ConversationFlowState.offer, reason="phase_offer_no_field_question"),
    )
    assert r.response_mode is ResponseMode.offer
    assert r.next_question is None
    assert r.key_talking_points == EDUCATION_CONVERSATION_FLOW.offer_framing[:3]
    assert r.tone_hints == ("confident", "clear_next_step", "not_pushy")
    assert r.strategy_reason_code == "state_offer"


def test_objection_mode_uses_niche_objection_hints() -> None:
    r = _plan(
        state=ConversationFlowState.objection_handling,
        intent=ConversationDetectedIntent.support,
        qp=_qp(
            hold=True,
            state=ConversationFlowState.objection_handling,
            reason="phase_objection_handling_no_field_question",
        ),
    )
    assert r.response_mode is ResponseMode.handle_objection
    assert r.next_question is None
    assert r.key_talking_points == EDUCATION_CONVERSATION_FLOW.objection_handling_hints[:3]
    assert r.tone_hints == ("empathetic", "factual", "offer_alternatives")
    assert r.strategy_reason_code == "state_objection"


def test_closing_mode_uses_niche_closing_objectives() -> None:
    r = _plan(
        state=ConversationFlowState.closing,
        intent=ConversationDetectedIntent.sales_interest,
        qp=_qp(hold=True, state=ConversationFlowState.closing, reason="phase_closing_no_field_question"),
    )
    assert r.response_mode is ResponseMode.closing_prompt
    assert r.next_question is None
    assert r.key_talking_points == EDUCATION_CONVERSATION_FLOW.closing_objectives[:3]
    assert r.tone_hints == ("confirming", "action_oriented")
    assert r.strategy_reason_code == "state_closing"


def test_fallback_state_mode_recovery_and_optional_question() -> None:
    r_no_q = _plan(
        state=ConversationFlowState.fallback,
        intent=ConversationDetectedIntent.unknown,
        qp=_qp(hold=True, state=ConversationFlowState.fallback, reason="intent_unknown", suggested=None),
    )
    assert r_no_q.response_mode is ResponseMode.fallback_response
    assert r_no_q.next_question is None
    assert r_no_q.key_talking_points == EDUCATION_CONVERSATION_FLOW.qualification_goals[:2]
    assert r_no_q.tone_hints == ("patient", "simple_language", "recover")
    r_with_q = _plan(
        state=ConversationFlowState.fallback,
        intent=ConversationDetectedIntent.unknown,
        qp=_qp(
            hold=False,
            state=ConversationFlowState.fallback,
            intent=ConversationDetectedIntent.unknown,
            suggested="Would online or in-person work better?",
            reason="fallback_recovery",
        ),
    )
    assert r_with_q.response_mode is ResponseMode.fallback_response
    assert r_with_q.next_question == "Would online or in-person work better?"


def test_fallback_mode_default_path_qualification_hold_without_bridge() -> None:
    """No question and not qualification_core_complete → default_fallback talking points."""
    r = _plan(
        state=ConversationFlowState.qualification,
        intent=ConversationDetectedIntent.unknown,
        qp=_qp(hold=True, reason="qualification_gathering", suggested=None),
    )
    assert r.response_mode is ResponseMode.fallback_response
    assert r.strategy_reason_code == "default_fallback"
    assert r.key_talking_points == EDUCATION_CONVERSATION_FLOW.qualification_goals[:2]
    assert r.next_question is None


def test_offer_mode_reusable_second_niche() -> None:
    r = plan_response_strategy(
        ResponsePlannerInput(
            niche_flow=HEALTHCARE_CONVERSATION_FLOW,
            current_state=ConversationFlowState.offer,
            detected_intent=ConversationDetectedIntent.sales_interest,
            question_plan=_qp(hold=True, state=ConversationFlowState.offer, reason="phase_offer_no_field_question"),
        ),
    )
    assert r.response_mode is ResponseMode.offer
    assert r.key_talking_points == HEALTHCARE_CONVERSATION_FLOW.offer_framing[:3]
    assert r.prompt_builder_context.niche_id == "healthcare"


# --- Output structure: stable, AI-ready ---


def test_response_mode_enum_values_stable_for_api() -> None:
    assert set(ResponseMode) == set(ResponseMode.__members__.values())
    for m in ResponseMode:
        assert m.value == m.name
        assert isinstance(m.value, str)
        assert m.value in _EXPECTED_MODES


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _plan(
            state=ConversationFlowState.start,
            intent=ConversationDetectedIntent.greeting,
            qp=_qp(
                state=ConversationFlowState.start,
                intent=ConversationDetectedIntent.greeting,
                suggested="Q?",
            ),
        ),
        lambda: _plan(
            state=ConversationFlowState.qualification,
            intent=ConversationDetectedIntent.unknown,
            qp=_qp(suggested="Q?"),
        ),
        lambda: _plan(
            state=ConversationFlowState.offer,
            intent=ConversationDetectedIntent.sales_interest,
            qp=_qp(hold=True, state=ConversationFlowState.offer, reason="phase_offer_no_field_question"),
        ),
        lambda: _plan(
            state=ConversationFlowState.objection_handling,
            intent=ConversationDetectedIntent.support,
            qp=_qp(hold=True, state=ConversationFlowState.objection_handling, reason="x"),
        ),
        lambda: _plan(
            state=ConversationFlowState.closing,
            intent=ConversationDetectedIntent.sales_interest,
            qp=_qp(hold=True, state=ConversationFlowState.closing, reason="x"),
        ),
        lambda: _plan(
            state=ConversationFlowState.fallback,
            intent=ConversationDetectedIntent.unknown,
            qp=_qp(hold=True, state=ConversationFlowState.fallback, suggested=None, reason="x"),
        ),
    ],
)
def test_response_strategy_has_required_ai_ready_fields(factory) -> None:
    r: ResponseStrategy = factory()
    assert isinstance(r.response_mode, ResponseMode)
    assert isinstance(r.key_talking_points, tuple) and all(isinstance(x, str) for x in r.key_talking_points)
    assert r.next_question is None or isinstance(r.next_question, str)
    assert isinstance(r.tone_hints, tuple) and all(isinstance(x, str) for x in r.tone_hints)
    assert isinstance(r.strategy_reason_code, str) and r.strategy_reason_code
    assert isinstance(r.prompt_builder_context, PromptBuilderContextSlice)


def test_prompt_builder_context_serializes_to_json_for_llm_metadata() -> None:
    r = _plan(
        state=ConversationFlowState.qualification,
        intent=ConversationDetectedIntent.faq,
        qp=_qp(suggested="One thing?", target="subject", desc="Subject line"),
    )
    ctx = r.prompt_builder_context
    payload = {
        "niche_id": ctx.niche_id,
        "conversation_phase": ctx.conversation_phase,
        "detected_intent": ctx.detected_intent,
        "response_mode": ctx.response_mode,
        "planner_action": ctx.planner_action,
        "planner_reason_code": ctx.planner_reason_code,
        "target_field_key": ctx.target_field_key,
        "field_description": ctx.field_description,
        "qualification_goals": list(ctx.qualification_goals),
        "suggest_set_qualification_complete": ctx.suggest_set_qualification_complete,
        "suggest_set_clarification_complete": ctx.suggest_set_clarification_complete,
        "all_core_fields_collected": ctx.all_core_fields_collected,
    }
    raw = json.dumps(payload, ensure_ascii=True)
    assert "education" in raw
    round_trip = json.loads(raw)
    assert round_trip["response_mode"] == r.response_mode.value


def test_full_strategy_serializes_for_orchestration_logging() -> None:
    r = _plan(
        state=ConversationFlowState.offer,
        intent=ConversationDetectedIntent.sales_interest,
        qp=_qp(hold=True, state=ConversationFlowState.offer, reason="phase_offer_no_field_question"),
    )
    blob = {
        "response_mode": r.response_mode.value,
        "strategy_reason_code": r.strategy_reason_code,
        "key_talking_points": list(r.key_talking_points),
        "next_question": r.next_question,
        "tone_hints": list(r.tone_hints),
    }
    json.dumps(blob, ensure_ascii=True)


def test_dataclasses_are_frozen() -> None:
    r = _plan(
        state=ConversationFlowState.closing,
        intent=ConversationDetectedIntent.greeting,
        qp=_qp(hold=True, state=ConversationFlowState.closing, reason="x"),
    )
    with pytest.raises(Exception):
        r.response_mode = ResponseMode.offer  # type: ignore[misc]
    with pytest.raises(Exception):
        r.prompt_builder_context.niche_id = "x"  # type: ignore[misc]
