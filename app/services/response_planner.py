"""
**Response planning** — maps funnel state, intent, and :class:`QuestionPlannerResult` to a
stable :class:`ResponseStrategy` for downstream prompt assembly and NLG.

This module does **not** render final assistant messages and is **not** merged into
:class:`~app.prompting.builder`; callers pass :attr:`ResponseStrategy.prompt_builder_context`
into :class:`~app.prompting.types.PromptExtensionContext` (or a future parallel field) when
wiring orchestration.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from app.lib.niche_flow.schema import NicheConversationFlowDefinition
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.services.conversation_state_machine import coerce_conversation_state, coerce_detected_intent
from app.services.question_planner import QuestionPlannerAction, QuestionPlannerResult


class ResponseMode(str, Enum):
    """Stable high-level response shape (orchestration + prompt hints)."""

    greet = "greet"
    ask_question = "ask_question"
    acknowledge_and_ask = "acknowledge_and_ask"
    offer = "offer"
    handle_objection = "handle_objection"
    closing_prompt = "closing_prompt"
    fallback_response = "fallback_response"


@dataclass(frozen=True, slots=True)
class PromptBuilderContextSlice:
    """
    JSON-serializable-friendly context for the prompt builder / orchestrator.

    Values are plain strings/tuples so they can be copied into ``PromptExtensionContext``
    or logged without custom encoders.
    """

    niche_id: str
    conversation_phase: str
    detected_intent: str
    response_mode: str
    planner_action: str
    planner_reason_code: str
    target_field_key: str | None
    field_description: str | None
    qualification_goals: tuple[str, ...]
    suggest_set_qualification_complete: bool
    suggest_set_clarification_complete: bool
    all_core_fields_collected: bool


@dataclass(frozen=True, slots=True)
class ResponseStrategy:
    """Structured response plan — no final natural language body."""

    response_mode: ResponseMode
    key_talking_points: tuple[str, ...]
    next_question: str | None
    tone_hints: tuple[str, ...]
    prompt_builder_context: PromptBuilderContextSlice
    strategy_reason_code: str


@dataclass(frozen=True, slots=True)
class ResponsePlannerInput:
    niche_flow: NicheConversationFlowDefinition
    current_state: ConversationFlowState | str | None
    detected_intent: ConversationDetectedIntent | str | None
    question_plan: QuestionPlannerResult
    collected_data: Mapping[str, object] | None = None


_INTENTS_ACK_FIRST: frozenset[ConversationDetectedIntent] = frozenset(
    {
        ConversationDetectedIntent.sales_interest,
        ConversationDetectedIntent.consulting,
        ConversationDetectedIntent.support,
        ConversationDetectedIntent.faq,
    },
)

_TONE_BY_MODE: dict[ResponseMode, tuple[str, ...]] = {
    ResponseMode.greet: ("warm", "brief", "welcoming"),
    ResponseMode.ask_question: ("curious", "single_question", "not_overwhelming"),
    ResponseMode.acknowledge_and_ask: ("warm", "brief_acknowledgment", "single_question"),
    ResponseMode.offer: ("confident", "clear_next_step", "not_pushy"),
    ResponseMode.handle_objection: ("empathetic", "factual", "offer_alternatives"),
    ResponseMode.closing_prompt: ("confirming", "action_oriented"),
    ResponseMode.fallback_response: ("patient", "simple_language", "recover"),
}


def _take_up_to(items: tuple[str, ...], n: int) -> tuple[str, ...]:
    return items[:n] if items else ()


def _pb_context(
    *,
    flow: NicheConversationFlowDefinition,
    state: ConversationFlowState,
    intent: ConversationDetectedIntent,
    mode: ResponseMode,
    qp: QuestionPlannerResult,
) -> PromptBuilderContextSlice:
    return PromptBuilderContextSlice(
        niche_id=flow.niche_id,
        conversation_phase=state.value,
        detected_intent=intent.value,
        response_mode=mode.value,
        planner_action=qp.action.value,
        planner_reason_code=qp.planner_reason_code,
        target_field_key=qp.target_field_key,
        field_description=qp.field_spec_description,
        qualification_goals=flow.qualification_goals,
        suggest_set_qualification_complete=qp.suggest_set_qualification_complete,
        suggest_set_clarification_complete=qp.suggest_set_clarification_complete,
        all_core_fields_collected=qp.all_core_fields_collected,
    )


def _strategy(
    *,
    mode: ResponseMode,
    points: tuple[str, ...],
    next_q: str | None,
    reason: str,
    flow: NicheConversationFlowDefinition,
    state: ConversationFlowState,
    intent: ConversationDetectedIntent,
    qp: QuestionPlannerResult,
) -> ResponseStrategy:
    return ResponseStrategy(
        response_mode=mode,
        key_talking_points=points,
        next_question=next_q,
        tone_hints=_TONE_BY_MODE[mode],
        prompt_builder_context=_pb_context(flow=flow, state=state, intent=intent, mode=mode, qp=qp),
        strategy_reason_code=reason,
    )


def plan_response_strategy(inp: ResponsePlannerInput) -> ResponseStrategy:
    """
    Decide how the assistant should shape the *next* reply (mode, bullets, question, tone).

    Deterministic; niche-agnostic aside from copy pulled from ``niche_flow``.
    """
    state, _ = coerce_conversation_state(inp.current_state)
    intent = coerce_detected_intent(inp.detected_intent)
    flow = inp.niche_flow
    qp = inp.question_plan

    next_q = qp.suggested_question_text
    has_question = bool(next_q and next_q.strip())

    # --- Phase-locked modes (state machine wins) ---
    if state == ConversationFlowState.completed:
        return _strategy(
            mode=ResponseMode.fallback_response,
            points=_take_up_to(flow.closing_objectives, 1)
            or ("Close politely; the conversation is marked complete.",),
            next_q=None,
            reason="terminal_completed",
            flow=flow,
            state=state,
            intent=intent,
            qp=qp,
        )

    if state == ConversationFlowState.offer:
        return _strategy(
            mode=ResponseMode.offer,
            points=_take_up_to(flow.offer_framing, 3),
            next_q=None,
            reason="state_offer",
            flow=flow,
            state=state,
            intent=intent,
            qp=qp,
        )

    if state == ConversationFlowState.objection_handling:
        return _strategy(
            mode=ResponseMode.handle_objection,
            points=_take_up_to(flow.objection_handling_hints, 3),
            next_q=None,
            reason="state_objection",
            flow=flow,
            state=state,
            intent=intent,
            qp=qp,
        )

    if state == ConversationFlowState.closing:
        return _strategy(
            mode=ResponseMode.closing_prompt,
            points=_take_up_to(flow.closing_objectives, 3),
            next_q=None,
            reason="state_closing",
            flow=flow,
            state=state,
            intent=intent,
            qp=qp,
        )

    if state == ConversationFlowState.fallback:
        return _strategy(
            mode=ResponseMode.fallback_response,
            points=_take_up_to(flow.qualification_goals, 2)
            or ("Gently steer back to how you can help.",),
            next_q=next_q if has_question else None,
            reason="state_fallback",
            flow=flow,
            state=state,
            intent=intent,
            qp=qp,
        )

    # --- Entry / gathering ---
    if state == ConversationFlowState.start and intent is ConversationDetectedIntent.greeting:
        return _strategy(
            mode=ResponseMode.greet,
            points=_take_up_to(flow.qualification_goals, 2),
            next_q=next_q,
            reason="start_greeting",
            flow=flow,
            state=state,
            intent=intent,
            qp=qp,
        )

    if qp.action is QuestionPlannerAction.engage_opening:
        return _strategy(
            mode=ResponseMode.ask_question,
            points=_take_up_to(flow.qualification_goals, 1),
            next_q=next_q,
            reason="planner_engage_opening",
            flow=flow,
            state=state,
            intent=intent,
            qp=qp,
        )

    if state == ConversationFlowState.clarification and has_question:
        clar_points = ("Resolve one ambiguity at a time; stay concise and empathetic.",)
        if intent in _INTENTS_ACK_FIRST:
            return _strategy(
                mode=ResponseMode.acknowledge_and_ask,
                points=clar_points,
                next_q=next_q,
                reason="clarification_question_with_substantive_intent",
                flow=flow,
                state=state,
                intent=intent,
                qp=qp,
            )
        return _strategy(
            mode=ResponseMode.ask_question,
            points=clar_points,
            next_q=next_q,
            reason="clarification_question_direct",
            flow=flow,
            state=state,
            intent=intent,
            qp=qp,
        )

    # Qualification complete hold: bridge toward summary / next step without duplicating questions
    if (
        state in (ConversationFlowState.qualification, ConversationFlowState.start)
        and qp.action is QuestionPlannerAction.hold_no_question
        and qp.planner_reason_code == "qualification_core_complete"
    ):
        return _strategy(
            mode=ResponseMode.acknowledge_and_ask,
            points=_take_up_to(flow.offer_framing, 2)
            + ("Core details are sufficient to outline a fit; avoid interrogating further.",),
            next_q=None,
            reason="qualification_complete_bridge",
            flow=flow,
            state=state,
            intent=intent,
            qp=qp,
        )

    if has_question:
        if intent in _INTENTS_ACK_FIRST:
            return _strategy(
                mode=ResponseMode.acknowledge_and_ask,
                points=_take_up_to(flow.qualification_goals, 1),
                next_q=next_q,
                reason="question_with_substantive_intent",
                flow=flow,
                state=state,
                intent=intent,
                qp=qp,
            )
        return _strategy(
            mode=ResponseMode.ask_question,
            points=_take_up_to(flow.qualification_goals, 1),
            next_q=next_q,
            reason="question_direct",
            flow=flow,
            state=state,
            intent=intent,
            qp=qp,
        )

    # Clarification exhausted or hold without question
    if state == ConversationFlowState.clarification:
        return _strategy(
            mode=ResponseMode.acknowledge_and_ask,
            points=_take_up_to(flow.clarification_question_examples, 1)
            + ("Move forward once ambiguity is resolved.",),
            next_q=None,
            reason="clarification_hold",
            flow=flow,
            state=state,
            intent=intent,
            qp=qp,
        )

    return _strategy(
        mode=ResponseMode.fallback_response,
        points=_take_up_to(flow.qualification_goals, 2),
        next_q=None,
        reason="default_fallback",
        flow=flow,
        state=state,
        intent=intent,
        qp=qp,
    )


__all__ = [
    "PromptBuilderContextSlice",
    "ResponseMode",
    "ResponsePlannerInput",
    "ResponseStrategy",
    "plan_response_strategy",
]
