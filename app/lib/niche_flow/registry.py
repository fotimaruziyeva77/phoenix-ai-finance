"""
Lookup :class:`~app.lib.niche_flow.schema.NicheConversationFlowDefinition` by ``niche_id``.

Ids align with :func:`~app.lib.niche_registry.list_supported_niches` and frontend
``SUPPORTED_NICHE_IDS``. Aliases normalize hyphenated ids to underscore form.
"""

from __future__ import annotations

from types import MappingProxyType

from app.lib.niche_flow.dev_agency import DEV_AGENCY_CONVERSATION_FLOW
from app.lib.niche_flow.education import EDUCATION_CONVERSATION_FLOW
from app.lib.niche_flow.healthcare import HEALTHCARE_CONVERSATION_FLOW
from app.lib.niche_flow.schema import CollectedFieldSpec, NicheConversationFlowDefinition
from app.lib.niche_flow.services import SERVICES_CONVERSATION_FLOW

_ALL_FLOWS: tuple[NicheConversationFlowDefinition, ...] = (
    EDUCATION_CONVERSATION_FLOW,
    HEALTHCARE_CONVERSATION_FLOW,
    DEV_AGENCY_CONVERSATION_FLOW,
    SERVICES_CONVERSATION_FLOW,
)

GENERIC_CONVERSATION_FLOW = NicheConversationFlowDefinition(
    niche_id="generic",
    qualification_goals=(
        "Understand the user’s goal and constraints before proposing a solution.",
        "Capture enough structured fields to route or quote without guessing.",
    ),
    core_fields=(
        CollectedFieldSpec(
            key="primary_need",
            description="Short label for what the user wants.",
            required_for_qualification=True,
        ),
        CollectedFieldSpec(
            key="context",
            description="Free-form context slug or category if known.",
            required_for_qualification=False,
        ),
    ),
    qualification_question_examples=(
        "What are you trying to achieve in one sentence?",
        "Is there a deadline or budget we should know about?",
    ),
    clarification_question_examples=(
        "Can you give an example of what success looks like for you?",
    ),
    offer_framing=(
        "Summarize what you can deliver and the next concrete step.",
    ),
    objection_handling_hints=(
        "Acknowledge the concern; separate facts from preferences; offer alternatives.",
    ),
    closing_objectives=(
        "Confirm agreement on next step, contact channel, and timing.",
    ),
)

_BY_ID: dict[str, NicheConversationFlowDefinition] = {
    f.niche_id: f for f in _ALL_FLOWS
}
NICHE_CONVERSATION_FLOWS: MappingProxyType[str, NicheConversationFlowDefinition] = MappingProxyType(
    _BY_ID
)


def normalize_niche_flow_id(niche_id: str | None) -> str:
    s = (niche_id or "").strip().lower().replace("-", "_")
    if s == "devagency":
        return "dev_agency"
    return s


def get_niche_conversation_flow(niche_id: str | None) -> NicheConversationFlowDefinition | None:
    """Return the flow for a supported niche, or ``None`` if unknown."""
    key = normalize_niche_flow_id(niche_id)
    return _BY_ID.get(key)


def get_niche_conversation_flow_or_generic(niche_id: str | None) -> NicheConversationFlowDefinition:
    """Return the niche flow or :data:`GENERIC_CONVERSATION_FLOW` when id is missing/unknown."""
    return get_niche_conversation_flow(niche_id) or GENERIC_CONVERSATION_FLOW


def list_niche_conversation_flows() -> tuple[NicheConversationFlowDefinition, ...]:
    """All configured niche flows, stable order (education → healthcare → dev_agency → services)."""
    return _ALL_FLOWS


def supported_niche_flow_ids() -> frozenset[str]:
    return frozenset(_BY_ID.keys())
