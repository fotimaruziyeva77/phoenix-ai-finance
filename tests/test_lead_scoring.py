"""Unit tests for deterministic :mod:`app.services.lead_scoring` with realistic niche payloads."""

from __future__ import annotations

import pytest
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.services.lead_scoring import (
    DEFAULT_LEAD_SCORING_CONFIG,
    NICHE_SCORING_CONFIG,
    LeadScoringConfig,
    score_lead,
)

# --- 1. Empty / weak lead scores low ---


def test_empty_lead_unknown_intent_no_data_start_state_is_cold_and_low() -> None:
    """No intent signal, no slots, no phone, earliest funnel → bottom of range."""
    r = score_lead(
        niche_id="education",
        detected_intent=None,
        collected_data_json={},
        phone=None,
        conversation_state=ConversationFlowState.start.value,
    )
    assert r.breakdown[0] == ("intent", 0)
    assert r.breakdown[1] == ("qualification_depth", 0)
    assert r.breakdown[2] == ("phone", 0)
    assert r.breakdown[3] == ("funnel_depth", 0)
    assert r.score == 0
    assert r.temperature == "cold"


def test_weak_lead_greeting_only_stays_cold() -> None:
    """Casual intent and no qualification progress should not reach warm."""
    r = score_lead(
        niche_id="healthcare",
        detected_intent=ConversationDetectedIntent.greeting.value,
        collected_data_json={},
        phone=None,
        conversation_state=ConversationFlowState.start.value,
    )
    assert r.score <= DEFAULT_LEAD_SCORING_CONFIG.temperature_cold_max
    assert r.temperature == "cold"


# --- 2. Partially qualified → medium (warm band under default config) ---


def test_partially_qualified_one_of_two_required_fields_is_warm_not_hot() -> None:
    """
    Education now has a single required core field, so qualification depth is all-or-nothing: any
    present required field yields full qualification points and pushes the score into the hot band.
    To exercise the *warm* band we model a genuinely partial lead — engaged and contactable (phone
    present) but the required core field is still missing, so qualification depth is 0.

    Sales intent + phone + clarification funnel → lands in warm band, not hot.
    """
    r = score_lead(
        niche_id="education",
        detected_intent=ConversationDetectedIntent.sales_interest.value,
        collected_data_json={"phone": "+15551234567"},
        phone=None,
        conversation_state=ConversationFlowState.clarification.value,
    )
    # 20 intent + 0 qual (required field absent) + 15 phone + 10 funnel = 45
    assert r.score == 45
    assert r.temperature == "warm"
    assert DEFAULT_LEAD_SCORING_CONFIG.temperature_cold_max < r.score <= DEFAULT_LEAD_SCORING_CONFIG.temperature_warm_max


@pytest.mark.parametrize(
    "niche_id,partial_collected",
    [
        # Required core field still missing (so qualification depth is 0) but a contact phone is
        # present alongside other non-required context — a genuinely partial, contactable lead.
        (
            "healthcare",
            {"appointment_type": "cleaning", "phone": "+15551234567"},
        ),
        (
            "dev_agency",
            {"website_or_bot_or_crm": "website", "phone": "+15551234567"},
        ),
        (
            "services",
            {"urgency": "this week", "phone": "+15551234567"},
        ),
    ],
)
def test_partial_qualification_medium_band_across_other_niches(
    niche_id: str,
    partial_collected: dict[str, object],
) -> None:
    """Same pattern across niches: required field absent (qual 0) but engaged + contactable →
    sales + phone + clarification funnel lands in the warm band, not cold/hot."""
    r = score_lead(
        niche_id=niche_id,
        detected_intent=ConversationDetectedIntent.sales_interest.value,
        collected_data_json=partial_collected,
        phone=None,
        conversation_state=ConversationFlowState.clarification.value,
    )
    assert r.temperature == "warm"
    # 20 intent + 0 qual (required field absent) + 15 phone + 10 funnel = 45
    assert r.score == 45


# --- 3. Strong qualification + phone scores high (hot) ---


def test_strong_education_lead_with_phone_closing_is_hot() -> None:
    r = score_lead(
        niche_id="education",
        detected_intent=ConversationDetectedIntent.sales_interest.value,
        collected_data_json={
            "student_grade": "Grade 10",
            "subject": "Physics",
            "lesson_format": "online",
            "branch_or_location": "North campus",
        },
        phone="+15551234567",
        conversation_state=ConversationFlowState.closing.value,
    )
    # 20 + 45 + 15 + 18 = 98
    assert r.score == 98
    assert r.temperature == "hot"
    assert r.breakdown[2] == ("phone", 15)


@pytest.mark.parametrize(
    "niche_id,collected,phone",
    [
        (
            "healthcare",
            {
                "specialty": "Family medicine",
                "appointment_type": "first visit",
                "preferred_time": "mornings",
                "branch_or_location": "Main clinic",
            },
            "+1-415-555-0199",
        ),
        (
            "dev_agency",
            {
                "requested_solution": "Marketing site + lead bot",
                "website_or_bot_or_crm": "website",
                "payment_needed": "10–15k band",
                "rough_scope": "MVP in 8 weeks",
            },
            "+447700900123",
        ),
        (
            "services",
            {
                "service_type": "HVAC repair",
                "location": "Austin, TX — 78704",
                "urgency": "this week",
                "availability": "weekday afternoons",
            },
            "+1-512-555-0142",
        ),
    ],
)
def test_strong_qualified_lead_with_phone_hot_each_core_niche(
    niche_id: str,
    collected: dict[str, object],
    phone: str,
) -> None:
    """All four niches: both required core fields + phone + late funnel → hot."""
    r = score_lead(
        niche_id=niche_id,
        detected_intent=ConversationDetectedIntent.sales_interest.value,
        collected_data_json=collected,
        phone=phone,
        conversation_state=ConversationFlowState.closing.value,
    )
    assert r.score >= 65
    assert r.temperature == "hot"
    assert r.breakdown[1][1] == 45
    assert r.breakdown[2][1] == 15


# --- 4. Temperature mapping (explicit boundaries) ---


def test_temperature_cold_at_cold_max_boundary() -> None:
    cfg = LeadScoringConfig(
        temperature_cold_max=40,
        temperature_warm_max=70,
        max_intent_points=40,
        intent_points={ConversationDetectedIntent.sales_interest.value: 40},
        max_qualification_points=0,
        max_phone_points=0,
        max_funnel_points=0,
    )
    r = score_lead(
        niche_id="education",
        detected_intent=ConversationDetectedIntent.sales_interest.value,
        collected_data_json={},
        conversation_state=ConversationFlowState.start.value,
        config=cfg,
    )
    assert r.score == 40
    assert r.temperature == "cold"


def test_temperature_warm_just_above_cold_max() -> None:
    cfg = LeadScoringConfig(
        temperature_cold_max=40,
        temperature_warm_max=70,
        max_intent_points=41,
        intent_points={ConversationDetectedIntent.sales_interest.value: 41},
        max_qualification_points=0,
        max_phone_points=0,
        max_funnel_points=0,
    )
    r = score_lead(
        niche_id="education",
        detected_intent=ConversationDetectedIntent.sales_interest.value,
        collected_data_json={},
        conversation_state=ConversationFlowState.start.value,
        config=cfg,
    )
    assert r.score == 41
    assert r.temperature == "warm"


def test_temperature_hot_just_above_warm_max() -> None:
    cfg = LeadScoringConfig(
        temperature_cold_max=40,
        temperature_warm_max=70,
        max_intent_points=71,
        intent_points={ConversationDetectedIntent.sales_interest.value: 71},
        max_qualification_points=0,
        max_phone_points=0,
        max_funnel_points=0,
    )
    r = score_lead(
        niche_id="education",
        detected_intent=ConversationDetectedIntent.sales_interest.value,
        collected_data_json={},
        conversation_state=ConversationFlowState.start.value,
        config=cfg,
    )
    assert r.score == 71
    assert r.temperature == "hot"


# --- 5. Deterministic ---


def test_scoring_is_deterministic_across_runs() -> None:
    kwargs = dict(
        niche_id="services",
        detected_intent=ConversationDetectedIntent.consulting.value,
        collected_data_json={"service_type": "Electrical", "location": "Denver"},
        phone=None,
        conversation_state=ConversationFlowState.offer.value,
    )
    results = [score_lead(**kwargs) for _ in range(5)]
    first = results[0]
    for r in results[1:]:
        assert r.score == first.score
        assert r.temperature == first.temperature
        assert r.breakdown == first.breakdown


# --- 6. Regression / plumbing ---


def test_phone_detected_from_collected_json_key() -> None:
    r = score_lead(
        niche_id="generic",
        detected_intent=ConversationDetectedIntent.greeting.value,
        collected_data_json={"phone": "+1 555 000 1111"},
        phone=None,
        conversation_state=ConversationFlowState.qualification.value,
    )
    assert r.breakdown[2][1] == 15


def test_niche_override_config_used() -> None:
    custom = LeadScoringConfig(max_phone_points=0, max_funnel_points=0, max_qualification_points=0)
    NICHE_SCORING_CONFIG["custom_test_niche"] = custom
    try:
        r = score_lead(
            niche_id="custom_test_niche",
            detected_intent=ConversationDetectedIntent.sales_interest.value,
            collected_data_json={"phone": "x"},
            phone="+1",
            conversation_state=ConversationFlowState.completed.value,
        )
        assert r.breakdown[2][1] == 0
    finally:
        del NICHE_SCORING_CONFIG["custom_test_niche"]


def test_score_clamps_to_max_total() -> None:
    cfg = LeadScoringConfig(
        max_intent_points=50,
        intent_points={ConversationDetectedIntent.sales_interest.value: 50},
        max_qualification_points=50,
        max_phone_points=50,
        max_funnel_points=50,
    )
    r = score_lead(
        niche_id="education",
        detected_intent=ConversationDetectedIntent.sales_interest.value,
        collected_data_json={
            "student_grade": "9",
            "subject": "x",
            "lesson_format": "online",
            "branch_or_location": "y",
        },
        phone="+1",
        conversation_state=ConversationFlowState.completed.value,
        config=cfg,
    )
    assert r.score == 100
