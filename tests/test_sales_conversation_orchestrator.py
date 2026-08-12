"""Unit tests for sales orchestration helpers (no DB / provider)."""

from __future__ import annotations

from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.services.question_planner import QuestionPlannerAction, QuestionPlannerResult
from app.services.sales_conversation_orchestrator import (
    ORCH_TARGET_FIELD_KEY,
    QP_CLAR_ROUND_KEY,
    SalesTurnLeadHints,
    _apply_completion_flags_from_planner,
    _compose_lead_flow_hint,
    _core_field_snapshot,
    _read_clarification_round,
    _read_extraction_target,
    _sync_orchestrator_keys_after_prompt_plan,
)


def _dummy_qp(**kwargs: object) -> QuestionPlannerResult:
    defaults: dict[str, object] = {
        "action": QuestionPlannerAction.hold_no_question,
        "target_field_key": None,
        "suggested_question_text": None,
        "field_spec_description": None,
        "qualification_question_pool_index": None,
        "clarification_pool_index": None,
        "suggest_set_qualification_complete": False,
        "all_core_fields_collected": False,
        "suggest_set_clarification_complete": False,
        "planner_reason_code": "test",
        "effective_state": ConversationFlowState.qualification,
        "effective_intent": ConversationDetectedIntent.sales_interest,
        "next_clarification_round": 0,
    }
    defaults.update(kwargs)
    return QuestionPlannerResult(**defaults)  # type: ignore[arg-type]


def test_read_clarification_round() -> None:
    assert _read_clarification_round({}) == 0
    assert _read_clarification_round({QP_CLAR_ROUND_KEY: 2}) == 2
    assert _read_clarification_round({QP_CLAR_ROUND_KEY: "3"}) == 3


def test_read_extraction_target() -> None:
    assert _read_extraction_target({}) is None
    assert _read_extraction_target({ORCH_TARGET_FIELD_KEY: "subject"}) == "subject"
    assert _read_extraction_target({ORCH_TARGET_FIELD_KEY: "  "}) is None


def test_apply_completion_flags() -> None:
    d: dict[str, object] = {}
    _apply_completion_flags_from_planner(
        d,
        _dummy_qp(
            suggest_set_qualification_complete=True,
            suggest_set_clarification_complete=True,
        ),
    )
    assert d["qualification_complete"] is True
    assert d["clarification_complete"] is True


def test_sync_orchestrator_keys_sets_target_and_clar_round() -> None:
    d: dict[str, object] = {}
    qp = _dummy_qp(
        action=QuestionPlannerAction.ask_core_field,
        target_field_key="student_grade",
        next_clarification_round=2,
    )
    _sync_orchestrator_keys_after_prompt_plan(
        d,
        next_state=ConversationFlowState.qualification,
        qp=qp,
    )
    assert d[ORCH_TARGET_FIELD_KEY] == "student_grade"
    assert QP_CLAR_ROUND_KEY not in d

    d2: dict[str, object] = {}
    _sync_orchestrator_keys_after_prompt_plan(
        d2,
        next_state=ConversationFlowState.clarification,
        qp=_dummy_qp(next_clarification_round=1),
    )
    assert d2[QP_CLAR_ROUND_KEY] == 1


def test_sync_clears_target_when_none() -> None:
    d = {ORCH_TARGET_FIELD_KEY: "x"}
    _sync_orchestrator_keys_after_prompt_plan(
        d,
        next_state=ConversationFlowState.offer,
        qp=_dummy_qp(target_field_key=None),
    )
    assert ORCH_TARGET_FIELD_KEY not in d


def test_compose_lead_flow_hint_includes_mode_and_question() -> None:
    h = _compose_lead_flow_hint(
        response_mode="ask_question",
        talking_points=("Stay brief.",),
        next_question="What grade?",
        tone_hints=("warm", "brief"),
        target_field="student_grade",
    )
    assert "ask_question" in h
    assert "What grade?" in h
    assert "student_grade" in h


def test_core_field_snapshot_filters_keys() -> None:
    snap = _core_field_snapshot(
        {"student_grade": "9", "extra": 1},
        frozenset({"student_grade", "subject"}),
    )
    assert snap == {"student_grade": "9"}


def test_sales_turn_lead_hints_dataclass() -> None:
    h = SalesTurnLeadHints(
        niche_id="education",
        core_field_snapshot={"a": 1},
        funnel_state="qualification",
        qualification_complete=False,
        all_core_fields_collected=False,
    )
    assert h.niche_id == "education"
