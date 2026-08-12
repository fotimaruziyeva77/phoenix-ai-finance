"""Conversation state machine: transitions, guards, invalid input."""

from __future__ import annotations

import pytest
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.services.conversation_state_machine import (
    ALLOWED_TRANSITIONS,
    KEY_ACCEPT_OFFER,
    KEY_CLARIFICATION_COMPLETE,
    KEY_DEAL_FINALIZED,
    KEY_NEEDS_CLARIFICATION,
    KEY_OBJECTION_RAISED,
    KEY_OBJECTION_RESOLVED,
    KEY_QUALIFICATION_COMPLETE,
    LatestUserMessageMeta,
    StateMachineInput,
    coerce_conversation_state,
    coerce_detected_intent,
    peek_allowed_targets,
    transition_state,
    truthy_collected,
)


def test_coerce_invalid_state_string_to_fallback() -> None:
    s, bad = coerce_conversation_state("not_a_state")
    assert bad is True
    assert s == ConversationFlowState.fallback


def test_coerce_none_to_fallback() -> None:
    s, bad = coerce_conversation_state(None)
    assert bad is True
    assert s == ConversationFlowState.fallback


def test_start_to_qualification_when_intent_known() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.start,
            detected_intent=ConversationDetectedIntent.greeting,
        ),
    )
    assert r.next_state == ConversationFlowState.qualification
    assert r.rule_id == "start_to_qualification"
    assert r.reason == "progress"


def test_start_to_fallback_when_intent_unknown() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.start,
            detected_intent=ConversationDetectedIntent.unknown,
        ),
    )
    assert r.next_state == ConversationFlowState.fallback
    assert r.reason == "intent_unknown"


@pytest.mark.parametrize(
    "intent",
    [
        ConversationDetectedIntent.sales_interest,
        ConversationDetectedIntent.support,
        ConversationDetectedIntent.faq,
        ConversationDetectedIntent.consulting,
    ],
)
def test_start_accepts_all_non_unknown_intents(intent: ConversationDetectedIntent) -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.start,
            detected_intent=intent,
        ),
    )
    assert r.next_state == ConversationFlowState.qualification


def test_qualification_to_clarification_when_flag() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.qualification,
            detected_intent=ConversationDetectedIntent.sales_interest,
            collected_data={KEY_NEEDS_CLARIFICATION: True},
        ),
    )
    assert r.next_state == ConversationFlowState.clarification
    assert r.reason == "progress"


def test_qualification_to_offer_when_complete() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.qualification,
            detected_intent=ConversationDetectedIntent.sales_interest,
            collected_data={KEY_QUALIFICATION_COMPLETE: True},
        ),
    )
    assert r.next_state == ConversationFlowState.offer
    assert r.rule_id == "qualification_complete_to_offer"


def test_qualification_to_fallback_when_intent_unknown() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.qualification,
            detected_intent=ConversationDetectedIntent.unknown,
        ),
    )
    assert r.next_state == ConversationFlowState.fallback
    assert r.reason == "intent_unknown"


def test_clarification_to_fallback_when_intent_unknown() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.clarification,
            detected_intent=ConversationDetectedIntent.unknown,
        ),
    )
    assert r.next_state == ConversationFlowState.fallback


def test_qualification_holds_without_flags() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.qualification,
            detected_intent=ConversationDetectedIntent.faq,
        ),
    )
    assert r.next_state == ConversationFlowState.qualification
    assert r.reason == "hold"


def test_clarification_to_offer_when_complete() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.clarification,
            detected_intent=ConversationDetectedIntent.faq,
            collected_data={KEY_CLARIFICATION_COMPLETE: True},
        ),
    )
    assert r.next_state == ConversationFlowState.offer


def test_offer_to_objection_when_flag() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.offer,
            detected_intent=ConversationDetectedIntent.sales_interest,
            collected_data={KEY_OBJECTION_RAISED: True},
        ),
    )
    assert r.next_state == ConversationFlowState.objection_handling


def test_offer_to_closing_when_accept() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.offer,
            detected_intent=ConversationDetectedIntent.sales_interest,
            collected_data={KEY_ACCEPT_OFFER: True},
        ),
    )
    assert r.next_state == ConversationFlowState.closing


def test_objection_priority_over_accept() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.offer,
            detected_intent=ConversationDetectedIntent.sales_interest,
            collected_data={KEY_OBJECTION_RAISED: True, KEY_ACCEPT_OFFER: True},
        ),
    )
    assert r.next_state == ConversationFlowState.objection_handling


def test_objection_to_closing_when_resolved() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.objection_handling,
            detected_intent=ConversationDetectedIntent.sales_interest,
            collected_data={KEY_OBJECTION_RESOLVED: True},
        ),
    )
    assert r.next_state == ConversationFlowState.closing


def test_objection_resolved_without_known_intent() -> None:
    """Resolution flag wins; unknown intent alone would otherwise fallback."""
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.objection_handling,
            detected_intent=ConversationDetectedIntent.unknown,
            collected_data={KEY_OBJECTION_RESOLVED: True},
        ),
    )
    assert r.next_state == ConversationFlowState.closing


def test_closing_to_completed_when_finalized() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.closing,
            detected_intent=ConversationDetectedIntent.greeting,
            collected_data={KEY_DEAL_FINALIZED: True},
        ),
    )
    assert r.next_state == ConversationFlowState.completed
    assert r.reason == "progress"


def test_completed_is_terminal() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.completed,
            detected_intent=ConversationDetectedIntent.sales_interest,
            collected_data={KEY_DEAL_FINALIZED: False},
        ),
    )
    assert r.next_state == ConversationFlowState.completed
    assert r.reason == "terminal"


def test_fallback_recovery_to_qualification() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.fallback,
            detected_intent=ConversationDetectedIntent.greeting,
        ),
    )
    assert r.next_state == ConversationFlowState.qualification
    assert r.reason == "recover"


def test_fallback_holds_on_unknown_intent() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.fallback,
            detected_intent=ConversationDetectedIntent.unknown,
        ),
    )
    assert r.next_state == ConversationFlowState.fallback
    assert r.reason == "hold"


def test_invalid_db_state_runs_from_fallback_with_flag() -> None:
    r = transition_state(
        StateMachineInput(
            current_state="garbage_state_xyz",
            detected_intent=ConversationDetectedIntent.sales_interest,
        ),
    )
    assert r.was_current_state_invalid is True
    assert r.previous_state == ConversationFlowState.fallback
    assert r.next_state == ConversationFlowState.qualification


def test_empty_user_message_holds_qualification() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.qualification,
            detected_intent=ConversationDetectedIntent.faq,
            latest_user_message=LatestUserMessageMeta(is_empty=True),
        ),
    )
    assert r.next_state == ConversationFlowState.qualification
    assert r.rule_id == "guard_empty_user_message"


def test_loop_guard_triggers_on_oscillation() -> None:
    """Tail q,c,q,c + proposed c completes A,B,A,B oscillation → fallback."""
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.qualification,
            detected_intent=ConversationDetectedIntent.faq,
            collected_data={KEY_NEEDS_CLARIFICATION: True},
            recent_states=(
                ConversationFlowState.clarification,
                ConversationFlowState.qualification,
                ConversationFlowState.clarification,
            ),
        ),
    )
    assert r.next_state == ConversationFlowState.fallback
    assert r.reason == "loop_guard"
    assert r.rule_id == "loop_guard_oscillation"


def test_truthy_collected_string_yes() -> None:
    assert truthy_collected({KEY_ACCEPT_OFFER: "yes"}, KEY_ACCEPT_OFFER) is True


def test_peek_allowed_targets_matches_graph() -> None:
    oh = peek_allowed_targets(ConversationFlowState.objection_handling)
    assert ConversationFlowState.closing in oh
    assert ConversationFlowState.offer not in oh
    assert ConversationFlowState.offer in peek_allowed_targets(ConversationFlowState.clarification)


def test_coerce_detected_intent_garbage_to_unknown() -> None:
    assert coerce_detected_intent("nope") == ConversationDetectedIntent.unknown


def test_all_states_have_allowlist() -> None:
    for s in ConversationFlowState:
        assert s in ALLOWED_TRANSITIONS
        assert len(ALLOWED_TRANSITIONS[s]) >= 1


def test_determinism_repeated_calls_identical() -> None:
    inp = StateMachineInput(
        current_state=ConversationFlowState.offer,
        detected_intent=ConversationDetectedIntent.sales_interest,
        collected_data={KEY_ACCEPT_OFFER: True},
        niche_context="education",
        latest_user_message=LatestUserMessageMeta(is_empty=False, char_length=42),
        recent_states=(ConversationFlowState.qualification,),
    )
    first = transition_state(inp)
    for _ in range(24):
        again = transition_state(inp)
        assert again == first


def test_current_state_string_whitespace_normalized() -> None:
    r = transition_state(
        StateMachineInput(
            current_state="  START  ",
            detected_intent="greeting",
        ),
    )
    assert r.was_current_state_invalid is False
    assert r.previous_state == ConversationFlowState.start
    assert r.next_state == ConversationFlowState.qualification


def test_needs_clarification_takes_priority_over_qualification_complete() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.qualification,
            detected_intent=ConversationDetectedIntent.faq,
            collected_data={
                KEY_NEEDS_CLARIFICATION: True,
                KEY_QUALIFICATION_COMPLETE: True,
            },
        ),
    )
    assert r.next_state == ConversationFlowState.clarification
    assert r.rule_id == "qualification_needs_clarification"


def test_detected_intent_passed_as_string() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.start,
            detected_intent="consulting",
        ),
    )
    assert r.next_state == ConversationFlowState.qualification


def test_illegal_candidate_edge_normalized_to_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """If internal logic ever proposes a disallowed edge, force safe fallback."""

    def _forced_illegal(
        current: ConversationFlowState,
        intent,
        data,
        meta,
        niche,
    ):
        return ConversationFlowState.completed, "unit_test_forced", "progress"

    monkeypatch.setattr(
        "app.services.conversation_state_machine._compute_candidate",
        _forced_illegal,
    )
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.start,
            detected_intent=ConversationDetectedIntent.greeting,
        ),
    )
    assert r.next_state == ConversationFlowState.fallback
    assert r.reason == "illegal_transition"
    assert r.rule_id == "illegal_transition_blocked"


def test_loop_guard_does_not_trigger_on_simple_forward_path() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.qualification,
            detected_intent=ConversationDetectedIntent.sales_interest,
            collected_data={KEY_NEEDS_CLARIFICATION: True},
            recent_states=(),
        ),
    )
    assert r.next_state == ConversationFlowState.clarification
    assert r.reason == "progress"


def test_recent_states_with_invalid_entries_coerced_without_crash() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.qualification,
            detected_intent=ConversationDetectedIntent.faq,
            collected_data={KEY_NEEDS_CLARIFICATION: True},
            recent_states=("bad_state", ConversationFlowState.clarification, "???"),
        ),
    )
    assert r.next_state == ConversationFlowState.clarification


def test_offer_holds_when_no_decision_flags() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.offer,
            detected_intent=ConversationDetectedIntent.sales_interest,
            collected_data={},
        ),
    )
    assert r.next_state == ConversationFlowState.offer
    assert r.reason == "hold"


def test_objection_unknown_intent_fallback_without_resolution() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.objection_handling,
            detected_intent=ConversationDetectedIntent.unknown,
            collected_data={},
        ),
    )
    assert r.next_state == ConversationFlowState.fallback
    assert r.reason == "intent_unknown"


def test_truthy_collected_rejects_false_empty_and_garbage() -> None:
    assert truthy_collected({KEY_ACCEPT_OFFER: False}, KEY_ACCEPT_OFFER) is False
    assert truthy_collected({KEY_ACCEPT_OFFER: ""}, KEY_ACCEPT_OFFER) is False
    assert truthy_collected({KEY_ACCEPT_OFFER: "maybe"}, KEY_ACCEPT_OFFER) is False
    assert truthy_collected({KEY_ACCEPT_OFFER: "1"}, KEY_ACCEPT_OFFER) is True


def test_closing_holds_until_deal_finalized() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.closing,
            detected_intent=ConversationDetectedIntent.sales_interest,
            collected_data={KEY_DEAL_FINALIZED: False},
        ),
    )
    assert r.next_state == ConversationFlowState.closing
    assert r.reason == "hold"


def test_clarification_to_offer_via_qualification_complete_flag() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.clarification,
            detected_intent=ConversationDetectedIntent.faq,
            collected_data={KEY_QUALIFICATION_COMPLETE: True},
        ),
    )
    assert r.next_state == ConversationFlowState.offer
    assert r.rule_id == "clarification_to_offer"


def test_start_to_fallback_when_intent_string_invalid() -> None:
    r = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.start,
            detected_intent="not_an_intent_label",
        ),
    )
    assert r.next_state == ConversationFlowState.fallback


def test_frozen_transition_result_equality() -> None:
    a = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.start,
            detected_intent=ConversationDetectedIntent.greeting,
        ),
    )
    b = transition_state(
        StateMachineInput(
            current_state=ConversationFlowState.start,
            detected_intent=ConversationDetectedIntent.greeting,
        ),
    )
    assert a == b
    assert hash(a) == hash(b)
