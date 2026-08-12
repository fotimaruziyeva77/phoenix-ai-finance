"""Niche conversation flow definitions and registry."""

from __future__ import annotations

from app.lib.niche_flow import (
    GENERIC_CONVERSATION_FLOW,
    CollectedFieldSpec,
    NicheConversationFlowDefinition,
    get_niche_conversation_flow,
    get_niche_conversation_flow_or_generic,
    list_niche_conversation_flows,
    normalize_niche_flow_id,
    supported_niche_flow_ids,
)
from app.lib.niche_registry import list_supported_niches


def test_supported_niches_match_flow_ids() -> None:
    reg_ids = {n.id for n in list_supported_niches()}
    flow_ids = supported_niche_flow_ids()
    assert reg_ids == flow_ids


def test_all_flows_have_required_sections() -> None:
    for flow in list_niche_conversation_flows():
        assert flow.niche_id
        assert len(flow.qualification_goals) >= 1
        assert len(flow.core_fields) >= 1
        assert len(flow.qualification_question_examples) >= 1
        assert len(flow.clarification_question_examples) >= 1
        assert len(flow.offer_framing) >= 1
        assert len(flow.objection_handling_hints) >= 1
        assert len(flow.closing_objectives) >= 1
        keys = [f.key for f in flow.core_fields]
        assert len(keys) == len(set(keys))


def test_education_core_field_keys() -> None:
    flow = get_niche_conversation_flow("education")
    assert flow is not None
    keys = {f.key for f in flow.core_fields}
    assert keys == {"student_grade", "subject", "lesson_format", "branch_or_location"}
    assert any(f.required_for_qualification for f in flow.core_fields)


def test_healthcare_dev_agency_services_field_keys() -> None:
    h = get_niche_conversation_flow("healthcare")
    assert h is not None
    assert {f.key for f in h.core_fields} == {
        "specialty",
        "appointment_type",
        "preferred_time",
        "branch_or_location",
    }
    d = get_niche_conversation_flow("dev_agency")
    assert d is not None
    assert {f.key for f in d.core_fields} == {
        "requested_solution",
        "website_or_bot_or_crm",
        "payment_needed",
        "rough_scope",
    }
    s = get_niche_conversation_flow("services")
    assert s is not None
    assert {f.key for f in s.core_fields} == {
        "service_type",
        "location",
        "urgency",
        "availability",
    }


def test_unknown_niche_returns_none() -> None:
    assert get_niche_conversation_flow("ecommerce") is None
    assert get_niche_conversation_flow(None) is None


def test_generic_fallback_wrapper() -> None:
    g = get_niche_conversation_flow_or_generic("unknown_niche")
    assert g.niche_id == "generic"
    assert isinstance(g, NicheConversationFlowDefinition)


def test_normalize_hyphen_alias() -> None:
    assert normalize_niche_flow_id("DEV-AGENCY") == "dev_agency"
    assert get_niche_conversation_flow("dev-agency") is not None


def test_generic_flow_is_distinct_from_niches() -> None:
    assert GENERIC_CONVERSATION_FLOW.niche_id == "generic"
    assert GENERIC_CONVERSATION_FLOW not in list_niche_conversation_flows()


def test_field_specs_are_frozen_dataclasses() -> None:
    f = CollectedFieldSpec(key="k", description="d", required_for_qualification=True)
    assert isinstance(f, CollectedFieldSpec)
