"""
Read-only helpers for question planning and funnel orchestration.

Aligns with :class:`~app.models.conversation_flow.ConversationFlowState` phases that
carry natural-language guidance in :class:`~app.lib.niche_flow.schema.NicheConversationFlowDefinition`.
The state machine itself stays niche-agnostic; these hooks supply content/field targets.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.lib.niche_flow.schema import NicheConversationFlowDefinition
from app.models.conversation_flow import ConversationFlowState


def required_qualification_field_keys(flow: NicheConversationFlowDefinition) -> tuple[str, ...]:
    """Field keys that must be filled before treating qualification as structurally complete."""
    return tuple(f.key for f in flow.core_fields if f.required_for_qualification)


def optional_core_field_keys(flow: NicheConversationFlowDefinition) -> tuple[str, ...]:
    return tuple(f.key for f in flow.core_fields if not f.required_for_qualification)


def field_value_present(value: object) -> bool:
    """Whether ``collected_data_json`` value counts as answered for planning."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, set)):
        return len(value) > 0
    return True


def first_missing_required_field_key(
    flow: NicheConversationFlowDefinition,
    collected: Mapping[str, object] | None,
) -> str | None:
    """
    Next required core field key to ask for, in definition order.

    Returns ``None`` when all required fields have present values.
    """
    data = collected or {}
    for f in flow.core_fields:
        if not f.required_for_qualification:
            continue
        if not field_value_present(data.get(f.key)):
            return f.key
    return None


def qualification_question_pool(flow: NicheConversationFlowDefinition) -> tuple[str, ...]:
    """Example questions for the qualification phase (state machine: ``qualification``)."""
    return flow.qualification_question_examples


def clarification_question_pool(flow: NicheConversationFlowDefinition) -> tuple[str, ...]:
    """Example questions for clarification (``clarification``)."""
    return flow.clarification_question_examples


def flow_has_content_for_state(
    flow: NicheConversationFlowDefinition,
    state: ConversationFlowState,
) -> bool:
    """
    Whether this definition provides non-empty planner/state guidance for a funnel state.

    ``start``, ``fallback``, and ``completed`` are not driven by niche copy.
    """
    if state in (
        ConversationFlowState.start,
        ConversationFlowState.fallback,
        ConversationFlowState.completed,
    ):
        return True
    if state == ConversationFlowState.qualification:
        return bool(flow.qualification_goals and flow.qualification_question_examples and flow.core_fields)
    if state == ConversationFlowState.clarification:
        return bool(flow.clarification_question_examples)
    if state == ConversationFlowState.offer:
        return bool(flow.offer_framing)
    if state == ConversationFlowState.objection_handling:
        return bool(flow.objection_handling_hints)
    if state == ConversationFlowState.closing:
        return bool(flow.closing_objectives)
    return False
