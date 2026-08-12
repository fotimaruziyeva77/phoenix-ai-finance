"""Local and field services niche — trades, repairs, on-site work."""

from __future__ import annotations

from app.lib.niche_flow.schema import CollectedFieldSpec, NicheConversationFlowDefinition

SERVICES_CONVERSATION_FLOW = NicheConversationFlowDefinition(
    niche_id="services",
    qualification_goals=(
        "Identify what service they need and where (one qualifying question).",
        "Get enough context to dispatch or provide a quote.",
    ),
    core_fields=(
        CollectedFieldSpec(
            key="service_type",
            description="Trade or job category and general location (plumbing in Tashkent, etc.).",
            required_for_qualification=True,
        ),
        CollectedFieldSpec(
            key="location",
            description="Neighborhood, district, or full address depending on policy.",
            required_for_qualification=False,
        ),
        CollectedFieldSpec(
            key="urgency",
            description="Emergency, same-week, or flexible scheduling.",
            required_for_qualification=False,
        ),
        CollectedFieldSpec(
            key="availability",
            description="Customer windows for technician arrival.",
            required_for_qualification=False,
        ),
    ),
    qualification_question_examples=(
        "What kind of work do you need done, and where is the property?",
        "How urgent is it — emergency today or flexible this week?",
    ),
    clarification_question_examples=(
        "Do you need a quote first, or should we send a specialist directly?",
    ),
    offer_framing=(
        "Quote visit fee, estimated labor range, or flat package if policy allows.",
        "State what is included (diagnostic, materials estimate) and what requires approval.",
        "Offer the next available slot or queue position honestly.",
    ),
    objection_handling_hints=(
        "Price: compare to emergency vs scheduled rates; offer non-urgent slot discount if true.",
        "Trust: licensing, insurance, warranty on labor—only if accurate.",
        "Timing: if delayed, set revised ETA instead of vague promises.",
    ),
    closing_objectives=(
        "Confirm service address, contact on-site, and access instructions.",
        "Capture payment method or deposit policy acknowledgment.",
        "Send confirmation of appointment window and technician contact pattern.",
    ),
)
