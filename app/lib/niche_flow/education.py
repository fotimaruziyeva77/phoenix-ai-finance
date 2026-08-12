"""Education niche — courses, tutoring, learner fit."""

from __future__ import annotations

from app.lib.niche_flow.schema import CollectedFieldSpec, NicheConversationFlowDefinition

EDUCATION_CONVERSATION_FLOW = NicheConversationFlowDefinition(
    niche_id="education",
    qualification_goals=(
        "Understand who the learner is and what subject they need help with (one question).",
        "Get enough to recommend a program or next step.",
    ),
    core_fields=(
        CollectedFieldSpec(
            key="student_grade",
            description="Grade level or age band combined with subject interest.",
            required_for_qualification=True,
        ),
        CollectedFieldSpec(
            key="subject",
            description="Primary subject or exam focus (e.g. mathematics, IELTS).",
            required_for_qualification=False,
        ),
        CollectedFieldSpec(
            key="lesson_format",
            description="Online, in-person, group, or one-to-one preference.",
            required_for_qualification=False,
        ),
        CollectedFieldSpec(
            key="branch_or_location",
            description="Preferred campus, city, or branch when applicable.",
            required_for_qualification=False,
        ),
    ),
    qualification_question_examples=(
        "Who is the learner (grade/age) and what subject or exam are you looking for help with?",
        "Do you prefer online or in-person lessons?",
    ),
    clarification_question_examples=(
        "Any specific timeline — exam date or term start we should plan around?",
    ),
    offer_framing=(
        "Summarize the fit: level, subject, format, and suggested program or package name.",
        "State what is included (hours per week, materials, assessment) without overpromising outcomes.",
        "Give one clear next step: trial lesson, placement test, or enrollment link.",
    ),
    objection_handling_hints=(
        "Price: break down cost per lesson or month; mention payment plans if available.",
        "Time: propose alternate slots or shorter trial before a long commitment.",
        "Trust: offer syllabus outline, teacher qualifications, or refund/trial policy if applicable.",
    ),
    closing_objectives=(
        "Confirm the chosen format, branch or online access, and start date.",
        "Collect contact details and consent for follow-up or enrollment paperwork.",
        "Set expectation for who will reach out and when.",
    ),
)
