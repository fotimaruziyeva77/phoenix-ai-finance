"""Dev / agency niche — web, bots, integrations, CRM builds."""

from __future__ import annotations

from app.lib.niche_flow.schema import CollectedFieldSpec, NicheConversationFlowDefinition

DEV_AGENCY_CONVERSATION_FLOW = NicheConversationFlowDefinition(
    niche_id="dev_agency",
    qualification_goals=(
        "Understand what the client wants built and why (one qualifying question max).",
        "Get enough context to offer a meaningful next step.",
    ),
    core_fields=(
        CollectedFieldSpec(
            key="requested_solution",
            description="What they want built and why (e.g. website for sales, chatbot for leads, app for customers).",
            required_for_qualification=True,
        ),
        CollectedFieldSpec(
            key="website_or_bot_or_crm",
            description="Channel or system category: site, bot, app, CRM, API integration.",
            required_for_qualification=False,
        ),
        CollectedFieldSpec(
            key="payment_needed",
            description="Budget band, payment preference, or procurement constraints.",
            required_for_qualification=False,
        ),
        CollectedFieldSpec(
            key="rough_scope",
            description="Pages, integrations, users, languages, or MVP vs phase-2 hint.",
            required_for_qualification=False,
        ),
    ),
    qualification_question_examples=(
        "What would you like us to build, and what problem will it solve for your business?",
        "Is this mainly a website, a chatbot, a mobile app, or integrations/CRM work?",
    ),
    clarification_question_examples=(
        "Any specific timeline or budget range we should keep in mind?",
    ),
    offer_framing=(
        "Reflect scope in phases: discovery, build, launch, handover.",
        "Call out assumptions and what is out of scope to prevent scope creep disputes.",
        "Propose a concrete next step: workshop, written estimate, or paid discovery.",
    ),
    objection_handling_hints=(
        "Price vs offshore: emphasize risk, communication, and warranty/support window.",
        "Timeline: explain dependency on approvals, assets, and third-party APIs.",
        "Trust: reference similar projects, code ownership, and SLAs without exaggerating.",
    ),
    closing_objectives=(
        "Align on commercial path: fixed quote, retainer, or discovery first.",
        "Identify decision-maker, billing entity, and contract signatory.",
        "Schedule kickoff and list assets needed (brand, access, credentials).",
    ),
)
