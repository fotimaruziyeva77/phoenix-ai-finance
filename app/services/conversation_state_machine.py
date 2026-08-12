"""
Conversation funnel **state control** (no natural-language generation).

Deterministic transitions from ``current_state``, ``detected_intent``, ``collected_data``,
and optional niche / message metadata. Callers persist ``next_state`` on the conversation row.

**Invalid-state strategy**
    If ``current_state`` is missing, empty, or not a member of
    :class:`~app.models.conversation_flow.ConversationFlowState`, it is coerced to
    ``fallback`` before rules run (``was_current_state_invalid=True`` in the result). This
    avoids crashing on legacy rows and surfaces a recoverable branch (fallback →
    qualification when intent is known).

**Collected-data flags** (optional, niche-agnostic; callers set from orchestration / AI):

* ``qualification_complete`` — ready to leave qualification toward offer path.
* ``needs_clarification`` — force qualification → clarification.
* ``clarification_complete`` — leave clarification → offer.
* ``objection_raised`` — offer → objection_handling (wins over close).
* ``accept_offer`` — offer → closing when no active objection flag.
* ``objection_resolved`` — objection_handling → closing.
* ``deal_finalized`` — closing → completed.

Values are truthy if bool ``True`` or strings ``"1"``, ``"true"``, ``"yes"`` (case-insensitive).

**Loop guard**
    If the proposed transition would continue a two-state oscillation pattern in
    ``recent_states`` (A→B→A→B), the target is coerced to ``fallback`` instead.

**Illegal transitions**
    Any edge not listed in ``ALLOWED_TRANSITIONS`` is blocked; the machine returns
    ``fallback`` with reason ``illegal_transition``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState

# --- Stable keys in ``collected_data_json`` (string keys) ---
KEY_QUALIFICATION_COMPLETE: Final = "qualification_complete"
KEY_NEEDS_CLARIFICATION: Final = "needs_clarification"
KEY_CLARIFICATION_COMPLETE: Final = "clarification_complete"
KEY_OBJECTION_RAISED: Final = "objection_raised"
KEY_ACCEPT_OFFER: Final = "accept_offer"
KEY_OBJECTION_RESOLVED: Final = "objection_resolved"
KEY_DEAL_FINALIZED: Final = "deal_finalized"


@dataclass(frozen=True, slots=True)
class LatestUserMessageMeta:
    """Optional facts about the last user turn (no message text here)."""

    is_empty: bool = False
    char_length: int = 0


@dataclass(frozen=True, slots=True)
class StateMachineInput:
    """Inputs for a single transition evaluation."""

    current_state: ConversationFlowState | str | None
    detected_intent: ConversationDetectedIntent | str | None
    collected_data: Mapping[str, object] | None = None
    niche_context: str | None = None
    latest_user_message: LatestUserMessageMeta | None = None
    recent_states: Sequence[ConversationFlowState | str] | None = None


@dataclass(frozen=True, slots=True)
class StateTransitionResult:
    """Outcome of one transition step (for persistence and structured logs only)."""

    previous_state: ConversationFlowState
    next_state: ConversationFlowState
    reason: str
    rule_id: str
    was_current_state_invalid: bool = False


def coerce_conversation_state(value: ConversationFlowState | str | None) -> tuple[ConversationFlowState, bool]:
    """
    Parse DB/orchestration value into :class:`ConversationFlowState`.

    Returns ``(state, True)`` when the value was missing or not a valid member (coerced to ``fallback``).
    """
    if isinstance(value, ConversationFlowState):
        return value, False
    if value is None or not str(value).strip():
        return ConversationFlowState.fallback, True
    key = str(value).strip().lower()
    try:
        return ConversationFlowState(key), False
    except ValueError:
        return ConversationFlowState.fallback, True


def coerce_detected_intent(value: ConversationDetectedIntent | str | None) -> ConversationDetectedIntent:
    if isinstance(value, ConversationDetectedIntent):
        return value
    if value is None or not str(value).strip():
        return ConversationDetectedIntent.unknown
    key = str(value).strip().lower()
    try:
        return ConversationDetectedIntent(key)
    except ValueError:
        return ConversationDetectedIntent.unknown


def truthy_collected(data: Mapping[str, object] | None, key: str) -> bool:
    if not data or key not in data:
        return False
    v = data[key]
    if v is True:
        return True
    if isinstance(v, str) and v.strip().lower() in ("1", "true", "yes", "on"):
        return True
    return False


def _normalize_recent(
    seq: Sequence[ConversationFlowState | str] | None,
    *,
    max_len: int = 12,
) -> tuple[ConversationFlowState, ...]:
    if not seq:
        return ()
    out: list[ConversationFlowState] = []
    for item in seq[-max_len:]:
        s, _ = coerce_conversation_state(item)
        out.append(s)
    return tuple(out)


def _oscillation_if_appended(
    recent: tuple[ConversationFlowState, ...],
    current: ConversationFlowState,
    candidate: ConversationFlowState,
) -> bool:
    """
    True if appending ``candidate`` after ``recent + (current,)`` ends in A,B,A,B with A != B.
    """
    tail = recent[-3:] + (current, candidate)
    if len(tail) < 4:
        return False
    a, b, c, d = tail[-4:]
    return a == c and b == d and a != b


ALLOWED_TRANSITIONS: dict[ConversationFlowState, frozenset[ConversationFlowState]] = {
    ConversationFlowState.start: frozenset(
        {ConversationFlowState.qualification, ConversationFlowState.fallback},
    ),
    ConversationFlowState.qualification: frozenset(
        {
            ConversationFlowState.qualification,
            ConversationFlowState.clarification,
            ConversationFlowState.offer,
            ConversationFlowState.fallback,
        },
    ),
    ConversationFlowState.clarification: frozenset(
        {
            ConversationFlowState.clarification,
            ConversationFlowState.offer,
            ConversationFlowState.fallback,
        },
    ),
    ConversationFlowState.offer: frozenset(
        {
            ConversationFlowState.offer,
            ConversationFlowState.objection_handling,
            ConversationFlowState.closing,
            ConversationFlowState.fallback,
        },
    ),
    ConversationFlowState.objection_handling: frozenset(
        {
            ConversationFlowState.objection_handling,
            ConversationFlowState.closing,
            ConversationFlowState.fallback,
        },
    ),
    ConversationFlowState.closing: frozenset(
        {
            ConversationFlowState.closing,
            ConversationFlowState.completed,
            ConversationFlowState.fallback,
        },
    ),
    ConversationFlowState.fallback: frozenset(
        {
            ConversationFlowState.fallback,
            ConversationFlowState.qualification,
        },
    ),
    ConversationFlowState.completed: frozenset({ConversationFlowState.completed}),
}


def _intent_known(intent: ConversationDetectedIntent) -> bool:
    return intent is not ConversationDetectedIntent.unknown


def _compute_candidate(
    current: ConversationFlowState,
    intent: ConversationDetectedIntent,
    data: Mapping[str, object] | None,
    meta: LatestUserMessageMeta | None,
    niche: str | None,
) -> tuple[ConversationFlowState, str, str]:
    """
    Return (candidate_next_state, rule_id, reason_suffix).

    ``niche_context`` is accepted for future niche-specific tables; MVP does not branch on it.
    """
    _ = niche  # reserved for niche registry hooks (Sprint 8+)

    data = data or {}
    meta = meta or LatestUserMessageMeta()

    # Terminal: never leave completed
    if current == ConversationFlowState.completed:
        return ConversationFlowState.completed, "terminal_completed", "terminal"

    # Empty user input: hold position in gathering states (no fabricated progress)
    if meta.is_empty and current in (
        ConversationFlowState.qualification,
        ConversationFlowState.clarification,
        ConversationFlowState.offer,
        ConversationFlowState.objection_handling,
        ConversationFlowState.closing,
    ):
        return current, "guard_empty_user_message", "hold"

    # --- start ---
    if current == ConversationFlowState.start:
        if not _intent_known(intent):
            return ConversationFlowState.fallback, "start_intent_unknown", "intent_unknown"
        return ConversationFlowState.qualification, "start_to_qualification", "progress"

    # --- qualification ---
    if current == ConversationFlowState.qualification:
        if not _intent_known(intent):
            return ConversationFlowState.fallback, "qualification_intent_unknown", "intent_unknown"
        if truthy_collected(data, KEY_NEEDS_CLARIFICATION):
            return ConversationFlowState.clarification, "qualification_needs_clarification", "progress"
        if truthy_collected(data, KEY_QUALIFICATION_COMPLETE):
            return ConversationFlowState.offer, "qualification_complete_to_offer", "progress"
        return ConversationFlowState.qualification, "qualification_gathering", "hold"

    # --- clarification ---
    if current == ConversationFlowState.clarification:
        if not _intent_known(intent):
            return ConversationFlowState.fallback, "clarification_intent_unknown", "intent_unknown"
        if truthy_collected(data, KEY_CLARIFICATION_COMPLETE) or truthy_collected(
            data,
            KEY_QUALIFICATION_COMPLETE,
        ):
            return ConversationFlowState.offer, "clarification_to_offer", "progress"
        return ConversationFlowState.clarification, "clarification_gathering", "hold"

    # --- offer ---
    if current == ConversationFlowState.offer:
        if truthy_collected(data, KEY_OBJECTION_RAISED):
            return ConversationFlowState.objection_handling, "offer_objection", "progress"
        if truthy_collected(data, KEY_ACCEPT_OFFER):
            return ConversationFlowState.closing, "offer_accept_to_closing", "progress"
        return ConversationFlowState.offer, "offer_pending", "hold"

    # --- objection_handling ---
    if current == ConversationFlowState.objection_handling:
        if truthy_collected(data, KEY_OBJECTION_RESOLVED):
            return ConversationFlowState.closing, "objection_resolved_to_closing", "progress"
        if not _intent_known(intent):
            return ConversationFlowState.fallback, "objection_intent_unknown", "intent_unknown"
        return ConversationFlowState.objection_handling, "objection_handling_hold", "hold"

    # --- closing ---
    if current == ConversationFlowState.closing:
        if truthy_collected(data, KEY_DEAL_FINALIZED):
            return ConversationFlowState.completed, "closing_to_completed", "progress"
        return ConversationFlowState.closing, "closing_pending", "hold"

    # --- fallback (recovery) ---
    if current == ConversationFlowState.fallback:
        if _intent_known(intent):
            return ConversationFlowState.qualification, "fallback_recovery_to_qualification", "recover"
        return ConversationFlowState.fallback, "fallback_hold_unknown", "hold"

    # Should not reach: defensive
    return ConversationFlowState.fallback, "unexpected_state_fallback", "error"


def transition_state(inp: StateMachineInput) -> StateTransitionResult:
    """
    Compute the next conversation state from explicit rules and guards.

    Does not mutate ``collected_data`` or touch the database.
    """
    current, invalid = coerce_conversation_state(inp.current_state)
    intent = coerce_detected_intent(inp.detected_intent)
    recent = _normalize_recent(inp.recent_states)

    candidate, rule_id, kind = _compute_candidate(
        current,
        intent,
        inp.collected_data,
        inp.latest_user_message,
        inp.niche_context,
    )

    reason = kind
    if _oscillation_if_appended(recent, current, candidate):
        candidate = ConversationFlowState.fallback
        rule_id = "loop_guard_oscillation"
        reason = "loop_guard"
    elif candidate not in ALLOWED_TRANSITIONS.get(
        current,
        frozenset({ConversationFlowState.fallback}),
    ):
        candidate = ConversationFlowState.fallback
        rule_id = "illegal_transition_blocked"
        reason = "illegal_transition"

    return StateTransitionResult(
        previous_state=current,
        next_state=candidate,
        reason=reason,
        rule_id=rule_id,
        was_current_state_invalid=invalid,
    )


def peek_allowed_targets(current: ConversationFlowState) -> frozenset[ConversationFlowState]:
    """Read-only view of outgoing edges (for admin tools / tests)."""
    return ALLOWED_TRANSITIONS.get(current, frozenset())
