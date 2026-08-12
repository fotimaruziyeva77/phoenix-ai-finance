"""
Structured conversation-flow vocabulary for prompt orchestration and lead logic.

These are **content definitions** only: no HTTP, no model calls, no UI components.
Callers (prompt builder, future orchestrator) pull text by niche id.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CollectedFieldSpec:
    """Stable key for ``collected_data_json`` plus a short meaning for prompts/docs."""

    key: str
    description: str
    required_for_qualification: bool = False


@dataclass(frozen=True, slots=True)
class NicheConversationFlowDefinition:
    """
    Per-niche guidance for qualification → offer → close.

    All string tuples are **suggested copy** for LLM or human agents; keep them
    centralized here rather than duplicating across the codebase.
    """

    niche_id: str
    qualification_goals: tuple[str, ...]
    core_fields: tuple[CollectedFieldSpec, ...]
    qualification_question_examples: tuple[str, ...]
    clarification_question_examples: tuple[str, ...]
    offer_framing: tuple[str, ...]
    objection_handling_hints: tuple[str, ...]
    closing_objectives: tuple[str, ...]
