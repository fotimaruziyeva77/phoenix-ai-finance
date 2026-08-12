"""Small shared utilities (no heavy framework imports)."""

from app.lib.niche_flow import (
    GENERIC_CONVERSATION_FLOW,
    CollectedFieldSpec,
    NicheConversationFlowDefinition,
    get_niche_conversation_flow,
    get_niche_conversation_flow_or_generic,
    list_niche_conversation_flows,
    normalize_niche_flow_id,
    supported_niche_flow_ids,
)
from app.lib.niche_registry import (
    NicheDefinition,
    get_niche_by_id,
    list_supported_niches,
    validate_niche_id,
)

__all__ = [
    "CollectedFieldSpec",
    "GENERIC_CONVERSATION_FLOW",
    "NicheConversationFlowDefinition",
    "NicheDefinition",
    "get_niche_by_id",
    "get_niche_conversation_flow",
    "get_niche_conversation_flow_or_generic",
    "list_niche_conversation_flows",
    "list_supported_niches",
    "normalize_niche_flow_id",
    "supported_niche_flow_ids",
    "validate_niche_id",
]
