"""Healthcare niche — appointments and specialty routing (non-clinical advice)."""

from __future__ import annotations

from app.lib.niche_flow.schema import CollectedFieldSpec, NicheConversationFlowDefinition

HEALTHCARE_CONVERSATION_FLOW = NicheConversationFlowDefinition(
    niche_id="healthcare",
    qualification_goals=(
        "Identify the specialty or service needed (one qualifying question).",
        "Get enough to schedule or route appropriately.",
    ),
    core_fields=(
        CollectedFieldSpec(
            key="specialty",
            description="Department, specialty, or type of appointment needed.",
            required_for_qualification=True,
        ),
        CollectedFieldSpec(
            key="appointment_type",
            description="Consultation, follow-up, cleaning, diagnostic, or other visit type.",
            required_for_qualification=False,
        ),
        CollectedFieldSpec(
            key="preferred_time",
            description="Preferred day part, window, or timezone-aware preference.",
            required_for_qualification=False,
        ),
        CollectedFieldSpec(
            key="branch_or_location",
            description="Preferred clinic, hospital site, or city.",
            required_for_qualification=False,
        ),
    ),
    qualification_question_examples=(
        "What type of appointment or specialty are you looking for?",
        "Is this a first visit or a follow-up?",
    ),
    clarification_question_examples=(
        "Do you have a preferred day or time for your appointment?",
    ),
    offer_framing=(
        "Propose an available slot or waitlist option with location and clinician role (not diagnosis).",
        "State preparation steps (documents, fasting, arrival time) appropriate to appointment type.",
        "Remind that medical decisions belong to licensed providers during the visit.",
    ),
    objection_handling_hints=(
        "Wait time: offer alternative dates, locations, or telehealth if available.",
        "Cost/insurance: direct to billing or coverage check without speculating coverage.",
        "Anxiety: acknowledge and offer what to expect at check-in; avoid clinical reassurance.",
    ),
    closing_objectives=(
        "Confirm appointment type, location, and time in the patient’s local context.",
        "Verify contact phone/email for confirmations and reminders.",
        "State cancellation policy and who to call for rescheduling.",
    ),
)
