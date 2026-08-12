"""Guardrail: onboarding niche ids must match conversation-flow registry (Sprint 8 lead/CRM keys)."""

from __future__ import annotations

from app.lib.niche_flow.registry import supported_niche_flow_ids
from app.lib.niche_registry import list_supported_niches


def test_niche_registry_ids_match_conversation_flow_registry() -> None:
    reg_ids = {n.id for n in list_supported_niches()}
    flow_ids = supported_niche_flow_ids()
    assert reg_ids == flow_ids, (
        f"niche_registry ids {reg_ids!r} must equal niche_flow ids {flow_ids!r} "
        "(single key namespace for bots, funnels, and future CRM mapping)."
    )
