"""
Deterministic **question planner** for one-question-at-a-time UX.

**Design**
    * Inputs are the niche flow definition (copy + field specs), conversation state,
      ``collected_data_json``, and detected intent. No LLM calls.
    * Output is **structured** (:class:`QuestionPlannerResult`) so the response layer
      (template, rules, or future Gemini paraphrase) turns ``suggested_question_text``
      into the final user-visible message.
    * Qualification uses **definition order**: all required core fields first, then
      optional core fields. Each field maps to a qualification example question by
      **field index** (``min(index, len(examples) - 1)``) so niches with 4 fields and
      4 examples stay aligned.
    * Clarification uses a **monotonic round index** (caller-supplied). When rounds
      exhaust the niche clarification pool, the planner stops asking and can recommend
      setting ``clarification_complete`` for the state machine.
    * **Advance hints** mirror state-machine flags: when every required core field is
      present, ``suggest_set_qualification_complete`` is true (orchestrator may persist
      ``qualification_complete``). Optional fields can still be collected in parallel
      turns if the conversation remains in ``qualification``.

**Future AI phrasing**
    Keep using the same ``QuestionPlannerResult``; swap or wrap ``suggested_question_text``
    with a short model rewrite using ``target_field_key`` + ``field_spec_description``
    as constraints.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from app.lib.niche_flow.planner_hooks import field_value_present
from app.lib.niche_flow.schema import CollectedFieldSpec, NicheConversationFlowDefinition
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.services.conversation_state_machine import (
    KEY_CLARIFICATION_COMPLETE,
    KEY_QUALIFICATION_COMPLETE,
    coerce_conversation_state,
    coerce_detected_intent,
    truthy_collected,
)


class QuestionPlannerAction(str, Enum):
    """What the orchestration layer should do with this turn."""

    ask_core_field = "ask_core_field"
    ask_clarification = "ask_clarification"
    hold_no_question = "hold_no_question"
    engage_opening = "engage_opening"


@dataclass(frozen=True, slots=True)
class QuestionPlannerInput:
    """Inputs for a single planning step."""

    niche_flow: NicheConversationFlowDefinition
    current_state: ConversationFlowState | str | None
    collected_data: Mapping[str, object] | None = None
    detected_intent: ConversationDetectedIntent | str | None = None
    clarification_round: int = 0
    """How many clarification questions have already been asked in this clarification visit."""
    collect_optional_core_fields: bool = True
    """If False, do not ask optional core fields once all required fields are present."""


@dataclass(frozen=True, slots=True)
class QuestionPlannerResult:
    """Structured plan for one user turn (single question or explicit hold)."""

    action: QuestionPlannerAction
    target_field_key: str | None
    suggested_question_text: str | None
    """One short question; empty when ``action`` is ``hold_no_question`` (unless opening)."""
    field_spec_description: str | None
    qualification_question_pool_index: int | None
    clarification_pool_index: int | None

    suggest_set_qualification_complete: bool
    """True when every *required* core field has a present value (state-machine hint)."""
    all_core_fields_collected: bool
    """True when every core field (required and optional) has a present value."""
    suggest_set_clarification_complete: bool
    """True when clarification rounds have exhausted the niche pool (optional policy)."""

    planner_reason_code: str
    effective_state: ConversationFlowState
    effective_intent: ConversationDetectedIntent
    next_clarification_round: int
    """Persist this if you store clarification progress (e.g. in ``collected_data_json``)."""


def _field_order_index(flow: NicheConversationFlowDefinition, spec: CollectedFieldSpec) -> int:
    for i, f in enumerate(flow.core_fields):
        if f.key == spec.key:
            return i
    return 0


def _qualification_question_for_field(
    flow: NicheConversationFlowDefinition,
    spec: CollectedFieldSpec,
) -> tuple[str, int]:
    pool = flow.qualification_question_examples
    idx = _field_order_index(flow, spec)
    if not pool:
        text = f"Could you tell me a bit more about: {spec.description}"
        return text, 0
    q_i = min(max(idx, 0), len(pool) - 1)
    return pool[q_i], q_i


def _first_missing_core_field_spec(
    flow: NicheConversationFlowDefinition,
    data: Mapping[str, object],
    *,
    include_optional: bool,
) -> CollectedFieldSpec | None:
    for f in flow.core_fields:
        if not f.required_for_qualification:
            continue
        if not field_value_present(data.get(f.key)):
            return f
    if not include_optional:
        return None
    for f in flow.core_fields:
        if f.required_for_qualification:
            continue
        if not field_value_present(data.get(f.key)):
            return f
    return None


def _all_required_core_present(flow: NicheConversationFlowDefinition, data: Mapping[str, object]) -> bool:
    for f in flow.core_fields:
        if not f.required_for_qualification:
            continue
        if not field_value_present(data.get(f.key)):
            return False
    return True


def _all_core_present(flow: NicheConversationFlowDefinition, data: Mapping[str, object]) -> bool:
    for f in flow.core_fields:
        if not field_value_present(data.get(f.key)):
            return False
    return True


def _result_hold(
    *,
    reason: str,
    state: ConversationFlowState,
    intent: ConversationDetectedIntent,
    data: Mapping[str, object],
    flow: NicheConversationFlowDefinition,
    clar_round: int,
    collect_optional: bool,
) -> QuestionPlannerResult:
    req_done = _all_required_core_present(flow, data)
    all_done = _all_core_present(flow, data)
    _ = _first_missing_core_field_spec(flow, data, include_optional=collect_optional)
    return QuestionPlannerResult(
        action=QuestionPlannerAction.hold_no_question,
        target_field_key=None,
        suggested_question_text=None,
        field_spec_description=None,
        qualification_question_pool_index=None,
        clarification_pool_index=None,
        suggest_set_qualification_complete=req_done
        or truthy_collected(data, KEY_QUALIFICATION_COMPLETE),
        all_core_fields_collected=all_done,
        suggest_set_clarification_complete=truthy_collected(data, KEY_CLARIFICATION_COMPLETE),
        planner_reason_code=reason,
        effective_state=state,
        effective_intent=intent,
        next_clarification_round=clar_round,
    )


def plan_next_question(inp: QuestionPlannerInput) -> QuestionPlannerResult:
    """
    Produce exactly **one** next-step plan: either a single question or a hold signal.

    Does not call external AI. Text is taken from niche examples or a minimal template.
    """
    state, _invalid = coerce_conversation_state(inp.current_state)
    intent = coerce_detected_intent(inp.detected_intent)
    data = inp.collected_data or {}
    flow = inp.niche_flow
    clar_round = max(0, int(inp.clarification_round))

    # Terminal / post-sale: no scripted qualification question
    if state == ConversationFlowState.completed:
        return _result_hold(
            reason="terminal_completed",
            state=state,
            intent=intent,
            data=data,
            flow=flow,
            clar_round=clar_round,
            collect_optional=inp.collect_optional_core_fields,
        )

    # Offer / objection / closing: response layer owns wording; planner does not stack questions
    if state in (
        ConversationFlowState.offer,
        ConversationFlowState.objection_handling,
        ConversationFlowState.closing,
    ):
        return _result_hold(
            reason=f"phase_{state.value}_no_field_question",
            state=state,
            intent=intent,
            data=data,
            flow=flow,
            clar_round=clar_round,
            collect_optional=inp.collect_optional_core_fields,
        )

    # Clarification phase — one pool question per round
    if state == ConversationFlowState.clarification:
        pool = flow.clarification_question_examples
        if not pool:
            return QuestionPlannerResult(
                action=QuestionPlannerAction.hold_no_question,
                target_field_key=None,
                suggested_question_text=None,
                field_spec_description=None,
                qualification_question_pool_index=None,
                clarification_pool_index=None,
                suggest_set_qualification_complete=_all_required_core_present(flow, data),
                all_core_fields_collected=_all_core_present(flow, data),
                suggest_set_clarification_complete=True,
                planner_reason_code="clarification_empty_pool",
                effective_state=state,
                effective_intent=intent,
                next_clarification_round=clar_round,
            )
        if clar_round >= len(pool):
            return QuestionPlannerResult(
                action=QuestionPlannerAction.hold_no_question,
                target_field_key=None,
                suggested_question_text=None,
                field_spec_description=None,
                qualification_question_pool_index=None,
                clarification_pool_index=None,
                suggest_set_qualification_complete=_all_required_core_present(flow, data),
                all_core_fields_collected=_all_core_present(flow, data),
                suggest_set_clarification_complete=True,
                planner_reason_code="clarification_pool_exhausted",
                effective_state=state,
                effective_intent=intent,
                next_clarification_round=clar_round,
            )
        text = pool[clar_round]
        return QuestionPlannerResult(
            action=QuestionPlannerAction.ask_clarification,
            target_field_key=None,
            suggested_question_text=text,
            field_spec_description=None,
            qualification_question_pool_index=None,
            clarification_pool_index=clar_round,
            suggest_set_qualification_complete=_all_required_core_present(flow, data),
            all_core_fields_collected=_all_core_present(flow, data),
            suggest_set_clarification_complete=False,
            planner_reason_code="clarification_ask_one",
            effective_state=state,
            effective_intent=intent,
            next_clarification_round=clar_round + 1,
        )

    # start, fallback, qualification — field gathering
    planning_states = (
        ConversationFlowState.start,
        ConversationFlowState.fallback,
        ConversationFlowState.qualification,
    )
    if state not in planning_states:
        return _result_hold(
            reason="unexpected_state",
            state=state,
            intent=intent,
            data=data,
            flow=flow,
            clar_round=clar_round,
            collect_optional=inp.collect_optional_core_fields,
        )

    missing = _first_missing_core_field_spec(
        flow,
        data,
        include_optional=inp.collect_optional_core_fields,
    )
    all_done = _all_core_present(flow, data)

    if missing is None:
        return QuestionPlannerResult(
            action=QuestionPlannerAction.hold_no_question,
            target_field_key=None,
            suggested_question_text=None,
            field_spec_description=None,
            qualification_question_pool_index=None,
            clarification_pool_index=None,
            suggest_set_qualification_complete=_all_required_core_present(flow, data)
            or truthy_collected(data, KEY_QUALIFICATION_COMPLETE),
            all_core_fields_collected=all_done,
            suggest_set_clarification_complete=False,
            planner_reason_code="qualification_core_complete",
            effective_state=state,
            effective_intent=intent,
            next_clarification_round=clar_round,
        )

    text, q_i = _qualification_question_for_field(flow, missing)

    # Soft opening: unknown intent at funnel entry — still one question, short path
    if (
        intent is ConversationDetectedIntent.unknown
        and state in (ConversationFlowState.fallback, ConversationFlowState.start)
        and not field_value_present(data.get(missing.key))
    ):
        action = QuestionPlannerAction.engage_opening
        reason = "entry_unknown_intent_opening"
    else:
        action = QuestionPlannerAction.ask_core_field
        reason = "qualification_ask_one_core_field"

    return QuestionPlannerResult(
        action=action,
        target_field_key=missing.key,
        suggested_question_text=text,
        field_spec_description=missing.description,
        qualification_question_pool_index=q_i,
        clarification_pool_index=None,
        suggest_set_qualification_complete=_all_required_core_present(flow, data)
        or truthy_collected(data, KEY_QUALIFICATION_COMPLETE),
        all_core_fields_collected=all_done,
        suggest_set_clarification_complete=False,
        planner_reason_code=reason,
        effective_state=state,
        effective_intent=intent,
        next_clarification_round=clar_round,
    )
