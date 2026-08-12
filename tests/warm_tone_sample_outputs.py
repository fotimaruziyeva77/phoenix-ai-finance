"""
Curated **example assistant messages** that match warm-tone goals (concise, polite, one question).

Used by :mod:`tests.test_warm_tone_response_behavior` to validate heuristics and document
expected shape—not live model output.
"""

from __future__ import annotations

# Education — acknowledge grade signal, single follow-up.
SAMPLE_EDUCATION_ACK_AND_ASK = (
    "Thanks for mentioning Grade 11—that helps. Which subject should we focus on first?"
)

# Healthcare — acknowledge specialty, one scheduling-style question.
SAMPLE_HEALTHCARE_ACK_AND_ASK = (
    "Got it, pediatrics. Is this mainly a first visit or a follow-up appointment?"
)

# Dev / agency — acknowledge outcome, one scoping question.
SAMPLE_DEV_AGENCY_ACK_AND_ASK = (
    "Makes sense—you want to capture leads from the site. Is the first slice mainly a "
    "homepage chat widget, or a guided flow after they click “Contact”?"
)

# Services — acknowledge urgency context, one diagnostic question.
SAMPLE_SERVICES_ACK_AND_ASK = (
    "Understood—an active leak is stressful. Is water still flowing at the leak, or have you "
    "been able to shut it off at the main valve?"
)

# Short closure without a new question (still concise, human).
SAMPLE_EDUCATION_NO_NEW_QUESTION = (
    "Perfect—that gives us enough to suggest a trial slot. I’ll note online evenings and "
    "IB Physics. Someone from the team will confirm times shortly."
)

# Deliberately bad: verbose + multiple questions (should fail heuristics).
SAMPLE_ROBOTIC_VERBOSE_BAD = """As an AI assistant, I am here to help you with your request.
Could you please provide your name? What is your email? What is your budget? What is your timeline?
Additionally, please confirm your company size and industry vertical. Thank you for your cooperation.
"""
