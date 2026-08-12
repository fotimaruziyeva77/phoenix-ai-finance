"""Validation, planner hooks, and state-machine alignment for niche conversation flows."""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType

import pytest
from app.lib.niche_flow import (
    GENERIC_CONVERSATION_FLOW,
    get_niche_conversation_flow,
    get_niche_conversation_flow_or_generic,
    list_niche_conversation_flows,
)
from app.lib.niche_flow.education import EDUCATION_CONVERSATION_FLOW
from app.lib.niche_flow.planner_hooks import (
    clarification_question_pool,
    field_value_present,
    first_missing_required_field_key,
    flow_has_content_for_state,
    optional_core_field_keys,
    qualification_question_pool,
    required_qualification_field_keys,
)
from app.lib.niche_flow.registry import NICHE_CONVERSATION_FLOWS
from app.lib.niche_flow.schema import CollectedFieldSpec
from app.lib.niche_flow.validation import (
    assert_valid_niche_conversation_flow,
    validate_niche_conversation_flow,
)
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.services.conversation_state_machine import (
    KEY_QUALIFICATION_COMPLETE,
    StateMachineInput,
    transition_state,
)


@pytest.mark.parametrize(
    "niche_id",
    ("education", "healthcare", "dev_agency", "services"),
)
def test_each_supported_niche_loads_and_validates(niche_id: str) -> None:
    flow = get_niche_conversation_flow(niche_id)
    assert flow is not None
    assert flow.niche_id == niche_id
    assert validate_niche_conversation_flow(flow) == []
    assert_valid_niche_conversation_flow(flow)


def test_all_registered_niche_flows_validate() -> None:
    for flow in list_niche_conversation_flows():
        assert validate_niche_conversation_flow(flow) == [], flow.niche_id


def test_generic_flow_validates() -> None:
    assert validate_niche_conversation_flow(GENERIC_CONVERSATION_FLOW) == []


def test_assert_valid_rejects_generic_when_disallowed() -> None:
    with pytest.raises(ValueError, match="generic"):
        assert_valid_niche_conversation_flow(GENERIC_CONVERSATION_FLOW, allow_generic=False)


def test_validation_empty_niche_id() -> None:
    bad = replace(EDUCATION_CONVERSATION_FLOW, niche_id="")
    errs = validate_niche_conversation_flow(bad)
    assert any("niche_id" in e for e in errs)


def test_validation_bad_niche_id_pattern() -> None:
    bad = replace(EDUCATION_CONVERSATION_FLOW, niche_id="DevAgency")
    errs = validate_niche_conversation_flow(bad)
    assert any("niche_id" in e and "pattern" in e for e in errs)


def test_validation_empty_qualification_goals() -> None:
    bad = replace(EDUCATION_CONVERSATION_FLOW, qualification_goals=())
    errs = validate_niche_conversation_flow(bad)
    assert any("qualification_goals" in e for e in errs)


def test_validation_whitespace_only_question() -> None:
    bad = replace(EDUCATION_CONVERSATION_FLOW, qualification_question_examples=("   ",))
    errs = validate_niche_conversation_flow(bad)
    assert any("qualification_question_examples" in e for e in errs)


def test_validation_no_required_core_field() -> None:
    specs = tuple(
        CollectedFieldSpec(key=f.key, description=f.description, required_for_qualification=False)
        for f in EDUCATION_CONVERSATION_FLOW.core_fields
    )
    bad = replace(EDUCATION_CONVERSATION_FLOW, core_fields=specs)
    errs = validate_niche_conversation_flow(bad)
    assert any("required_for_qualification" in e for e in errs)


def test_validation_duplicate_core_field_keys() -> None:
    f0 = EDUCATION_CONVERSATION_FLOW.core_fields[0]
    dup = replace(
        EDUCATION_CONVERSATION_FLOW,
        core_fields=(
            CollectedFieldSpec(
                key=f0.key,
                description="first",
                required_for_qualification=True,
            ),
            CollectedFieldSpec(
                key=f0.key,
                description="second",
                required_for_qualification=False,
            ),
        ),
    )
    errs = validate_niche_conversation_flow(dup)
    assert any("duplicate" in e for e in errs)


def test_validation_invalid_field_key_pattern() -> None:
    bad = replace(
        EDUCATION_CONVERSATION_FLOW,
        core_fields=(
            CollectedFieldSpec(
                key="BadKey",
                description="desc",
                required_for_qualification=True,
            ),
        ),
    )
    errs = validate_niche_conversation_flow(bad)
    assert any("core_fields" in e and "key" in e for e in errs)


def test_registry_map_is_read_only() -> None:
    assert isinstance(NICHE_CONVERSATION_FLOWS, MappingProxyType)
    with pytest.raises(TypeError):
        NICHE_CONVERSATION_FLOWS["education"] = EDUCATION_CONVERSATION_FLOW  # type: ignore[index]


def test_lookup_never_raises_invalid_ids() -> None:
    for raw in (None, "", "   ", "not_a_niche", "ecommerce", "EDUCATION", "Education"):
        flow = get_niche_conversation_flow(raw)  # type: ignore[arg-type]
        assert flow is None or flow.niche_id in NICHE_CONVERSATION_FLOWS
    assert get_niche_conversation_flow("EDUCATION") is not None
    assert get_niche_conversation_flow("Education") is not None


def test_or_generic_never_returns_none() -> None:
    for raw in (None, "", "  ", "unknown", "bad-niche"):
        g = get_niche_conversation_flow_or_generic(raw)
        assert g is not None
        assert validate_niche_conversation_flow(g) == []


def test_planner_required_and_optional_keys_match_education() -> None:
    flow = EDUCATION_CONVERSATION_FLOW
    req = required_qualification_field_keys(flow)
    opt = optional_core_field_keys(flow)
    assert set(req) | set(opt) == {f.key for f in flow.core_fields}
    # Education now has a single required core field; the rest are optional.
    assert set(req) == {"student_grade"}
    assert set(opt) == {"subject", "lesson_format", "branch_or_location"}
    assert first_missing_required_field_key(flow, {}) == "student_grade"
    # Once the only required field is present, nothing further is required.
    assert first_missing_required_field_key(flow, {"student_grade": "9"}) is None
    assert first_missing_required_field_key(flow, {"student_grade": "9", "subject": "math"}) is None


def test_planner_ignores_whitespace_only_strings() -> None:
    flow = EDUCATION_CONVERSATION_FLOW
    assert first_missing_required_field_key(flow, {"student_grade": "  "}) == "student_grade"


def test_field_value_present() -> None:
    assert field_value_present("x") is True
    assert field_value_present("  ") is False
    assert field_value_present(None) is False
    assert field_value_present(0) is True
    assert field_value_present([]) is False
    assert field_value_present([1]) is True


def test_question_pools_non_empty_for_all_niches() -> None:
    for flow in list_niche_conversation_flows():
        assert len(qualification_question_pool(flow)) >= 1
        assert len(clarification_question_pool(flow)) >= 1


def test_flow_has_content_for_all_sales_states() -> None:
    sales_states = (
        ConversationFlowState.qualification,
        ConversationFlowState.clarification,
        ConversationFlowState.offer,
        ConversationFlowState.objection_handling,
        ConversationFlowState.closing,
    )
    for flow in list_niche_conversation_flows():
        for st in sales_states:
            assert flow_has_content_for_state(flow, st), (flow.niche_id, st)


def test_flow_has_content_for_non_niche_states() -> None:
    flow = EDUCATION_CONVERSATION_FLOW
    for st in (
        ConversationFlowState.start,
        ConversationFlowState.fallback,
        ConversationFlowState.completed,
    ):
        assert flow_has_content_for_state(flow, st) is True


def test_state_machine_ignores_invalid_niche_context_safely() -> None:
    """Niche id on the conversation row may be stale; transitions must not depend on registry."""
    for niche_ctx in (None, "", "   ", "typo_niche", "ecommerce"):
        result = transition_state(
            StateMachineInput(
                current_state=ConversationFlowState.qualification,
                detected_intent=ConversationDetectedIntent.sales_interest,
                collected_data={KEY_QUALIFICATION_COMPLETE: True},
                niche_context=niche_ctx,
            ),
        )
        assert result.next_state == ConversationFlowState.offer
        assert result.rule_id == "qualification_complete_to_offer"


def test_planner_flow_resolves_or_generic_for_state_machine_bot_niche() -> None:
    """Typical orchestration: resolve flow for prompt/planner even when DB niche is wrong."""
    bot_niche = "typo_or_legacy"
    flow = get_niche_conversation_flow_or_generic(bot_niche)
    assert flow.niche_id == "generic"
    assert flow_has_content_for_state(flow, ConversationFlowState.qualification)
    assert first_missing_required_field_key(flow, {}) == "primary_need"
