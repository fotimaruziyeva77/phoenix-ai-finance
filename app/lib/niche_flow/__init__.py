"""
Per-niche conversation flow definitions (qualification, clarification, offer, objections, closing).

Import from ``app.lib.niche_flow`` or ``app.lib`` re-exports. No provider or HTTP calls here.
"""

from __future__ import annotations

from app.lib.niche_flow.planner_hooks import (
    clarification_question_pool,
    field_value_present,
    first_missing_required_field_key,
    flow_has_content_for_state,
    optional_core_field_keys,
    qualification_question_pool,
    required_qualification_field_keys,
)
from app.lib.niche_flow.registry import (
    GENERIC_CONVERSATION_FLOW,
    NICHE_CONVERSATION_FLOWS,
    get_niche_conversation_flow,
    get_niche_conversation_flow_or_generic,
    list_niche_conversation_flows,
    normalize_niche_flow_id,
    supported_niche_flow_ids,
)
from app.lib.niche_flow.schema import CollectedFieldSpec, NicheConversationFlowDefinition
from app.lib.niche_flow.validation import (
    assert_valid_niche_conversation_flow,
    validate_niche_conversation_flow,
)

__all__ = [
    "CollectedFieldSpec",
    "GENERIC_CONVERSATION_FLOW",
    "NICHE_CONVERSATION_FLOWS",
    "NicheConversationFlowDefinition",
    "assert_valid_niche_conversation_flow",
    "clarification_question_pool",
    "field_value_present",
    "first_missing_required_field_key",
    "flow_has_content_for_state",
    "get_niche_conversation_flow",
    "get_niche_conversation_flow_or_generic",
    "list_niche_conversation_flows",
    "normalize_niche_flow_id",
    "optional_core_field_keys",
    "qualification_question_pool",
    "required_qualification_field_keys",
    "supported_niche_flow_ids",
    "validate_niche_conversation_flow",
]
