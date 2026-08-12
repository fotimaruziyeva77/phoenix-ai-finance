"""Collected-data extraction and safe merge."""

from __future__ import annotations

from app.lib.niche_flow.dev_agency import DEV_AGENCY_CONVERSATION_FLOW
from app.lib.niche_flow.education import EDUCATION_CONVERSATION_FLOW
from app.lib.niche_flow.healthcare import HEALTHCARE_CONVERSATION_FLOW
from app.lib.niche_flow.services import SERVICES_CONVERSATION_FLOW
from app.services.collected_data_extraction import (
    allowed_core_field_keys,
    apply_user_reply_to_collected_data,
    merge_collected_data,
    propose_extractions_from_user_message,
)


def test_merge_only_fills_empty_by_default() -> None:
    allowed = allowed_core_field_keys(EDUCATION_CONVERSATION_FLOW)
    prior = {"student_grade": "Grade 9", "subject": "Math"}
    merged = merge_collected_data(
        prior,
        {"student_grade": "Grade 12", "subject": "Physics"},
        allowed_keys=allowed,
        only_if_empty=True,
    )
    assert merged["student_grade"] == "Grade 9"
    assert merged["subject"] == "Math"


def test_merge_fills_missing_keys() -> None:
    allowed = allowed_core_field_keys(EDUCATION_CONVERSATION_FLOW)
    merged = merge_collected_data(
        {"student_grade": "Grade 9"},
        {"subject": "  IB Physics  "},
        allowed_keys=allowed,
    )
    assert merged["subject"] == "IB Physics"


def test_merge_drops_unknown_keys() -> None:
    allowed = allowed_core_field_keys(EDUCATION_CONVERSATION_FLOW)
    merged = merge_collected_data(
        {},
        {"subject": "x", "hacker_key": "pwnd"},
        allowed_keys=allowed,
    )
    assert "hacker_key" not in merged
    assert merged["subject"] == "x"


def test_merge_skips_blank_proposals() -> None:
    allowed = allowed_core_field_keys(EDUCATION_CONVERSATION_FLOW)
    merged = merge_collected_data({"subject": "A"}, {"subject": "   "}, allowed_keys=allowed)
    assert merged["subject"] == "A"


def test_merge_overwrite_when_keys_allow_overwrite() -> None:
    allowed = allowed_core_field_keys(EDUCATION_CONVERSATION_FLOW)
    merged = merge_collected_data(
        {"subject": "Old"},
        {"subject": "New"},
        allowed_keys=allowed,
        only_if_empty=True,
        keys_allow_overwrite=frozenset({"subject"}),
    )
    assert merged["subject"] == "New"


def test_education_grade_specialized() -> None:
    prop, audit = propose_extractions_from_user_message(
        "She is in grade 10 this year",
        EDUCATION_CONVERSATION_FLOW,
        target_field_key="student_grade",
    )
    assert prop.get("student_grade") == "Grade 10"
    assert any("specialized" in a for a in audit)


def test_education_student_grade_no_verbatim_for_punctuation_or_nonsense() -> None:
    for msg in ("?", "ok", "blue elephant sky"):
        prop, audit = propose_extractions_from_user_message(
            msg,
            EDUCATION_CONVERSATION_FLOW,
            target_field_key="student_grade",
        )
        assert prop == {}, msg
        assert not any("verbatim" in a for a in audit), msg


def test_education_student_grade_verbatim_single_number_word() -> None:
    prop, audit = propose_extractions_from_user_message(
        "nine",
        EDUCATION_CONVERSATION_FLOW,
        target_field_key="student_grade",
    )
    assert prop.get("student_grade") == "nine"
    assert any("verbatim" in a for a in audit)


def test_education_lesson_format_online() -> None:
    prop, _ = propose_extractions_from_user_message(
        "We'd prefer fully online lessons",
        EDUCATION_CONVERSATION_FLOW,
        target_field_key="lesson_format",
    )
    assert prop.get("lesson_format") == "online"


def test_education_subject_verbatim() -> None:
    prop, audit = propose_extractions_from_user_message(
        "Mostly struggling with calculus proofs",
        EDUCATION_CONVERSATION_FLOW,
        target_field_key="subject",
    )
    assert "calculus" in (prop.get("subject") or "").lower()
    assert any("verbatim" in a for a in audit)


def test_healthcare_appointment_type() -> None:
    prop, _ = propose_extractions_from_user_message(
        "It's my first visit to the clinic",
        HEALTHCARE_CONVERSATION_FLOW,
        target_field_key="appointment_type",
    )
    assert prop.get("appointment_type") == "first visit"


def test_healthcare_specialty_verbatim() -> None:
    prop, _ = propose_extractions_from_user_message(
        "Pediatric cardiology",
        HEALTHCARE_CONVERSATION_FLOW,
        target_field_key="specialty",
    )
    assert prop["specialty"] == "Pediatric cardiology"


def test_dev_agency_channel_chatbot() -> None:
    prop, _ = propose_extractions_from_user_message(
        "We need a chatbot on the marketing site",
        DEV_AGENCY_CONVERSATION_FLOW,
        target_field_key="website_or_bot_or_crm",
    )
    assert prop.get("website_or_bot_or_crm") == "chatbot"


def test_dev_agency_solution_verbatim() -> None:
    prop, _ = propose_extractions_from_user_message(
        "Automate booking from Instagram DMs",
        DEV_AGENCY_CONVERSATION_FLOW,
        target_field_key="requested_solution",
    )
    assert "Instagram" in prop["requested_solution"]


def test_services_urgency() -> None:
    prop, _ = propose_extractions_from_user_message(
        "It's an emergency — water everywhere",
        SERVICES_CONVERSATION_FLOW,
        target_field_key="urgency",
    )
    assert prop.get("urgency") == "urgent"


def test_services_location_verbatim() -> None:
    prop, _ = propose_extractions_from_user_message(
        "Brooklyn, near Prospect Park",
        SERVICES_CONVERSATION_FLOW,
        target_field_key="location",
    )
    assert "Brooklyn" in prop["location"]


def test_apply_outcome_tracks_keys_written() -> None:
    out = apply_user_reply_to_collected_data(
        {"student_grade": "Grade 8"},
        "We want online sessions",
        EDUCATION_CONVERSATION_FLOW,
        target_field_key="lesson_format",
    )
    assert out.collected_data["student_grade"] == "Grade 8"
    assert out.collected_data["lesson_format"] == "online"
    assert "lesson_format" in out.keys_written
    assert out.proposed_extractions["lesson_format"] == "online"


def test_apply_does_not_overwrite_existing_subject() -> None:
    out = apply_user_reply_to_collected_data(
        {"subject": "Math"},
        "Actually physics would be better",
        EDUCATION_CONVERSATION_FLOW,
        target_field_key="subject",
    )
    assert out.collected_data["subject"] == "Math"
    assert "subject" not in out.keys_written


def test_services_urgency_with_explicit_target() -> None:
    prop, _ = propose_extractions_from_user_message(
        "This is quite urgent for us",
        SERVICES_CONVERSATION_FLOW,
        target_field_key="urgency",
    )
    assert prop.get("urgency") == "urgent"


def test_no_target_yields_empty_to_avoid_misattribution() -> None:
    """Without ``target_field_key``, we do not guess slots (orchestrator should pass planner target)."""
    prop, audit = propose_extractions_from_user_message(
        "This is quite urgent for us",
        SERVICES_CONVERSATION_FLOW,
        target_field_key=None,
    )
    assert prop == {}
    assert audit == ()


def test_allowed_keys_match_niche_core_fields() -> None:
    assert allowed_core_field_keys(EDUCATION_CONVERSATION_FLOW) == {
        "student_grade",
        "subject",
        "lesson_format",
        "branch_or_location",
    }


# --- Realistic per-niche mapping (user replies) ---


def test_education_maps_9th_grade_and_hybrid() -> None:
    g, _ = propose_extractions_from_user_message(
        "He's finishing 9th grade next month",
        EDUCATION_CONVERSATION_FLOW,
        target_field_key="student_grade",
    )
    assert g.get("student_grade") == "Grade 9"
    fmt, _ = propose_extractions_from_user_message(
        "Hybrid would work best — two days online, one in person",
        EDUCATION_CONVERSATION_FLOW,
        target_field_key="lesson_format",
    )
    assert fmt.get("lesson_format") == "hybrid"


def test_education_kindergarten_and_in_person() -> None:
    k, _ = propose_extractions_from_user_message(
        "She's in KG this year",
        EDUCATION_CONVERSATION_FLOW,
        target_field_key="student_grade",
    )
    assert k.get("student_grade") == "Kindergarten"
    ip, _ = propose_extractions_from_user_message(
        "We can only do in-person at your Midtown branch",
        EDUCATION_CONVERSATION_FLOW,
        target_field_key="lesson_format",
    )
    assert ip.get("lesson_format") == "in-person"


def test_education_branch_location_realistic() -> None:
    prop, _ = propose_extractions_from_user_message(
        "Downtown Seattle, close to Pike Place",
        EDUCATION_CONVERSATION_FLOW,
        target_field_key="branch_or_location",
    )
    assert prop["branch_or_location"] == "Downtown Seattle, close to Pike Place"


def test_healthcare_follow_up_and_preferred_time() -> None:
    ap, _ = propose_extractions_from_user_message(
        "Just a follow-up after last month's cleaning",
        HEALTHCARE_CONVERSATION_FLOW,
        target_field_key="appointment_type",
    )
    assert ap.get("appointment_type") == "follow-up"
    tm, _ = propose_extractions_from_user_message(
        "Tuesday mornings before 11 work best",
        HEALTHCARE_CONVERSATION_FLOW,
        target_field_key="preferred_time",
    )
    assert "Tuesday" in tm["preferred_time"]


def test_healthcare_branch_and_dentistry_specialty() -> None:
    br, _ = propose_extractions_from_user_message(
        "Main Street clinic in Portland",
        HEALTHCARE_CONVERSATION_FLOW,
        target_field_key="branch_or_location",
    )
    assert "Portland" in br["branch_or_location"]
    sp, _ = propose_extractions_from_user_message(
        "General dentistry, maybe a whitening consult too",
        HEALTHCARE_CONVERSATION_FLOW,
        target_field_key="specialty",
    )
    assert "dentistry" in sp["specialty"].lower()


def test_dev_agency_crm_and_budget_verbatim() -> None:
    ch, _ = propose_extractions_from_user_message(
        "We outgrew spreadsheets — need a lightweight CRM",
        DEV_AGENCY_CONVERSATION_FLOW,
        target_field_key="website_or_bot_or_crm",
    )
    assert ch.get("website_or_bot_or_crm") == "CRM"
    pay, _ = propose_extractions_from_user_message(
        "Roughly 8–12k for phase one, flexible on payment schedule",
        DEV_AGENCY_CONVERSATION_FLOW,
        target_field_key="payment_needed",
    )
    assert "12k" in pay["payment_needed"] or "8" in pay["payment_needed"]


def test_dev_agency_scope_verbatim_and_website_channel() -> None:
    sc, _ = propose_extractions_from_user_message(
        "About 12 pages, Stripe checkout, bilingual EN/ES",
        DEV_AGENCY_CONVERSATION_FLOW,
        target_field_key="rough_scope",
    )
    assert "Stripe" in sc["rough_scope"]
    wb, _ = propose_extractions_from_user_message(
        "Primarily a new marketing website",
        DEV_AGENCY_CONVERSATION_FLOW,
        target_field_key="website_or_bot_or_crm",
    )
    assert wb.get("website_or_bot_or_crm") == "website"


def test_services_service_type_and_availability() -> None:
    st, _ = propose_extractions_from_user_message(
        "AC not cooling — probably refrigerant or compressor",
        SERVICES_CONVERSATION_FLOW,
        target_field_key="service_type",
    )
    assert "AC" in st["service_type"] or "cooling" in st["service_type"].lower()
    av, _ = propose_extractions_from_user_message(
        "Home after 6pm weekdays or anytime Saturday",
        SERVICES_CONVERSATION_FLOW,
        target_field_key="availability",
    )
    assert "6pm" in av["availability"] or "Saturday" in av["availability"]


def test_services_flexible_urgency_and_location_address() -> None:
    u, _ = propose_extractions_from_user_message(
        "No rush — flexible over the next two weeks",
        SERVICES_CONVERSATION_FLOW,
        target_field_key="urgency",
    )
    assert u.get("urgency") == "flexible"
    loc, _ = propose_extractions_from_user_message(
        "123 Oak St, Unit 4B, Austin TX 78701",
        SERVICES_CONVERSATION_FLOW,
        target_field_key="location",
    )
    assert "78701" in loc["location"]


# --- Partial / fragile user input must not break stored data ---


def test_empty_user_message_leaves_data_unchanged() -> None:
    prior = {
        "student_grade": "Grade 7",
        "subject": "Algebra",
        "qualification_complete": True,
    }
    out = apply_user_reply_to_collected_data(
        prior,
        "   \n",
        EDUCATION_CONVERSATION_FLOW,
        target_field_key="lesson_format",
    )
    assert out.collected_data == prior
    assert out.keys_written == ()


def test_whitespace_only_proposal_does_not_clear_existing() -> None:
    allowed = allowed_core_field_keys(EDUCATION_CONVERSATION_FLOW)
    merged = merge_collected_data(
        {"subject": "Chemistry"},
        {"subject": "\t  \n"},
        allowed_keys=allowed,
        only_if_empty=False,
    )
    # Blank normalizes to skip in merge (no value to apply)
    assert merged["subject"] == "Chemistry"


def test_verbatim_too_long_does_not_set_field() -> None:
    long_msg = "x" * 450
    prop, _ = propose_extractions_from_user_message(
        long_msg,
        EDUCATION_CONVERSATION_FLOW,
        target_field_key="subject",
    )
    assert prop == {}


def test_merge_preserves_non_core_keys_and_state_flags() -> None:
    """JSON may hold planner/state keys outside niche core_fields; merge must not drop them."""
    allowed = allowed_core_field_keys(SERVICES_CONVERSATION_FLOW)
    prior: dict[str, object] = {
        "service_type": "Plumbing",
        "location": "Denver",
        "qualification_complete": True,
        "_internal_cursor": 3,
    }
    merged = merge_collected_data(
        prior,
        {"urgency": "flexible"},
        allowed_keys=allowed,
    )
    assert merged["qualification_complete"] is True
    assert merged["_internal_cursor"] == 3
    assert merged["service_type"] == "Plumbing"
    assert merged["location"] == "Denver"
    assert merged["urgency"] == "flexible"


def test_multi_turn_education_partial_answers_preserve_prior_slots() -> None:
    data: dict[str, object] = {}
    for msg, key in (
        ("10th grader", "student_grade"),
        ("Mostly AP Chemistry", "subject"),
    ):
        out = apply_user_reply_to_collected_data(data, msg, EDUCATION_CONVERSATION_FLOW, target_field_key=key)
        data = out.collected_data
    assert data["student_grade"] == "Grade 10"
    assert "Chemistry" in data["subject"]
    # Irrelevant follow-up targeting lesson_format must not wipe subject/grade
    out2 = apply_user_reply_to_collected_data(
        data,
        "hmm not sure",
        EDUCATION_CONVERSATION_FLOW,
        target_field_key="lesson_format",
    )
    assert out2.collected_data["student_grade"] == "Grade 10"
    assert "Chemistry" in out2.collected_data["subject"]
    assert out2.collected_data.get("lesson_format") == "hmm not sure"


def test_merge_only_if_empty_false_overwrites() -> None:
    allowed = allowed_core_field_keys(HEALTHCARE_CONVERSATION_FLOW)
    merged = merge_collected_data(
        {"specialty": "Old"},
        {"specialty": "New specialty"},
        allowed_keys=allowed,
        only_if_empty=False,
    )
    assert merged["specialty"] == "New specialty"


def test_apply_partial_proposal_only_touches_target_key() -> None:
    """Filling one empty core slot leaves other captured slots unchanged."""
    base = {
        "requested_solution": "Lead capture",
        "payment_needed": "5k retainer",
        "rough_scope": "MVP",
    }
    out = apply_user_reply_to_collected_data(
        base,
        "Actually we need HubSpot CRM integration too",
        DEV_AGENCY_CONVERSATION_FLOW,
        target_field_key="website_or_bot_or_crm",
    )
    assert out.collected_data["requested_solution"] == "Lead capture"
    assert out.collected_data["payment_needed"] == "5k retainer"
    assert out.collected_data["rough_scope"] == "MVP"
    assert out.collected_data["website_or_bot_or_crm"] == "CRM"


def test_channel_correction_requires_explicit_overwrite_when_already_set() -> None:
    """Safe default: do not replace a filled channel slot unless operator allows overwrite."""
    base = {
        "website_or_bot_or_crm": "website",
    }
    out = apply_user_reply_to_collected_data(
        base,
        "We meant a CRM build, not just a site",
        DEV_AGENCY_CONVERSATION_FLOW,
        target_field_key="website_or_bot_or_crm",
    )
    assert out.collected_data["website_or_bot_or_crm"] == "website"
    fixed = apply_user_reply_to_collected_data(
        base,
        "We meant a CRM build, not just a site",
        DEV_AGENCY_CONVERSATION_FLOW,
        target_field_key="website_or_bot_or_crm",
        keys_allow_overwrite=frozenset({"website_or_bot_or_crm"}),
    )
    assert fixed.collected_data["website_or_bot_or_crm"] == "CRM"
