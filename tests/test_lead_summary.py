"""Unit tests for :mod:`app.services.lead_summary` — realistic JSON, no hallucination, concise output."""

from __future__ import annotations

import pytest
from app.models.conversation_flow import ConversationFlowState
from app.services.lead_summary import DEFAULT_MAX_SUMMARY_LENGTH, generate_lead_summary

# Separator between body / funnel / recent (U+00B7 MIDDLE DOT, same as service).
_SEP = "\u00b7"


@pytest.fixture
def education_full_collected() -> dict[str, object]:
    return {
        "student_grade": "Grade 7",
        "subject": "math",
        "lesson_format": "in-person at branch",
    }


@pytest.fixture
def healthcare_full_collected() -> dict[str, object]:
    return {
        "specialty": "dentist",
        "appointment_type": "cleaning",
        "preferred_time": "tomorrow evening",
    }


@pytest.fixture
def dev_agency_full_collected() -> dict[str, object]:
    return {
        "requested_solution": "e-commerce website with Stripe checkout",
        "website_or_bot_or_crm": "website",
        "payment_needed": "15-25k",
    }


@pytest.fixture
def services_full_collected() -> dict[str, object]:
    return {
        "service_type": "plumbing leak",
        "location": "Mission District, SF",
        "urgency": "urgent same-day",
    }


def test_education_lead_summary_exact_body(education_full_collected: dict[str, object]) -> None:
    s = generate_lead_summary(
        niche_id="education",
        collected_data_json=education_full_collected,
        conversation_state=None,
    )
    assert s == "Parent/learner looking for in-person math (Grade 7)."


def test_education_lead_summary_with_funnel_state_appends_stage(
    education_full_collected: dict[str, object],
) -> None:
    s = generate_lead_summary(
        niche_id="education",
        collected_data_json=education_full_collected,
        conversation_state=ConversationFlowState.qualification.value,
    )
    assert s == f"Parent/learner looking for in-person math (Grade 7). {_SEP} Qualification"


def test_healthcare_lead_summary_exact(healthcare_full_collected: dict[str, object]) -> None:
    s = generate_lead_summary(
        niche_id="healthcare",
        collected_data_json=healthcare_full_collected,
    )
    assert (
        s == "Patient wants dentist appointment (cleaning); prefers tomorrow evening."
    )


def test_dev_agency_lead_summary_exact(dev_agency_full_collected: dict[str, object]) -> None:
    s = generate_lead_summary(
        niche_id="dev_agency",
        collected_data_json=dev_agency_full_collected,
    )
    assert (
        s
        == "Wants website work: e-commerce website with Stripe checkout. (budget signal: 15-25k)."
    )


def test_services_lead_summary_exact(services_full_collected: dict[str, object]) -> None:
    s = generate_lead_summary(
        niche_id="services",
        collected_data_json=services_full_collected,
    )
    assert s == "Needs urgent same-day plumbing leak in/near Mission District, SF."


def test_no_hallucinated_verticals_in_education_summary(
    education_full_collected: dict[str, object],
) -> None:
    """Template glue words OK; unrelated domain nouns from other niches must not appear."""
    s = generate_lead_summary(
        niche_id="education",
        collected_data_json=education_full_collected,
    ).lower()
    for foreign in ("plumb", "dentist", "patient wants", "wants website work", "hvac", "stripe"):
        assert foreign not in s, f"unexpected token: {foreign!r}"


def test_extra_json_keys_not_surfaced_in_education_summary() -> None:
    """Only whitelisted slot keys are read; arbitrary extra keys must not leak into text."""
    s = generate_lead_summary(
        niche_id="education",
        collected_data_json={
            "subject": "Violin",
            "student_grade": "Adult learner",
            "internal_ops_note": "DO NOT MENTION ACQUISITION",
        },
    )
    assert "ACQUISITION" not in s
    assert "DO NOT" not in s
    assert "Violin" in s
    assert "Adult learner" in s


def test_summary_concise_default_cap_for_rich_payloads(
    education_full_collected: dict[str, object],
    healthcare_full_collected: dict[str, object],
    dev_agency_full_collected: dict[str, object],
    services_full_collected: dict[str, object],
) -> None:
    for niche, data in (
        ("education", education_full_collected),
        ("healthcare", healthcare_full_collected),
        ("dev_agency", dev_agency_full_collected),
        ("services", services_full_collected),
    ):
        s = generate_lead_summary(niche_id=niche, collected_data_json=data)
        assert len(s) <= DEFAULT_MAX_SUMMARY_LENGTH
        assert len(s) <= 180, f"{niche} summary should stay short for MVP: {len(s)} chars"


def test_summary_concise_with_funnel_and_recent_clipped_to_max() -> None:
    long_tail = "word " * 60
    s = generate_lead_summary(
        niche_id="education",
        collected_data_json={"subject": "Algebra", "student_grade": "Grade 9"},
        conversation_state=ConversationFlowState.offer.value,
        recent_user_messages=["short", long_tail],
        max_length=120,
    )
    assert len(s) <= 120


def test_recent_user_message_is_verbatim_clip() -> None:
    s = generate_lead_summary(
        niche_id="education",
        collected_data_json={"subject": "Physics"},
        recent_user_messages=["", "  Need help before finals  "],
    )
    assert 'Recent: "Need help before finals"' in s


def test_empty_collected_falls_back_without_invented_slots() -> None:
    s = generate_lead_summary(
        niche_id="education",
        collected_data_json={},
        conversation_state=ConversationFlowState.start.value,
    )
    assert "Education: captured; no qualification fields filled yet." in s
    assert "Grade" not in s
    assert "math" not in s.lower()


def test_generic_niche_only_lists_core_fields_from_payload() -> None:
    s = generate_lead_summary(
        niche_id="generic",
        collected_data_json={
            "primary_need": "Quote for coaching",
            "context": "executive",
            "malicious_extra": "wire money now",
        },
    )
    assert "coaching" in s.lower()
    assert "executive" in s.lower()
    assert "wire money" not in s.lower()
