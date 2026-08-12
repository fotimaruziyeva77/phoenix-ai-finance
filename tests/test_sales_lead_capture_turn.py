"""Unit tests for :mod:`app.services.sales_lead_capture_turn` (no orchestrator)."""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.repositories.lead_repository import LeadRepository
from app.services.sales_lead_capture_turn import (
    CAPTURED_LEAD_ID_KEY,
    LEAD_CAPTURE_DONE_KEY,
    format_lead_capture_closing_message,
    is_lead_capture_marked_done,
    run_sales_lead_capture_after_pipeline,
)


def test_mark_done_and_detection() -> None:
    d: dict[str, object] = {}
    assert is_lead_capture_marked_done(d) is False
    lid = uuid.uuid4()
    d[LEAD_CAPTURE_DONE_KEY] = True
    d[CAPTURED_LEAD_ID_KEY] = str(lid)
    assert is_lead_capture_marked_done(d) is True


def test_format_closing_includes_bot_name() -> None:
    t = format_lead_capture_closing_message(bot_name="Acme", summary_line="Widgets order.")
    assert "Acme" in t
    assert "Widgets order." in t
    assert "Thank you" in t


def test_evaluate_gates_funnel_override_matches_orchestrator_contract() -> None:
    """ORM ``current_state`` can lag; orchestrator passes post-pipeline state into lead gates."""
    from app.services.lead_creation_service import evaluate_lead_creation_gates

    oid = uuid.uuid4()
    bot = SimpleNamespace(
        id=uuid.uuid4(),
        owner_id=oid,
        goal_type="sales",
        niche_id="generic",
        name="B",
    )
    conv = SimpleNamespace(
        id=uuid.uuid4(),
        bot_id=bot.id,
        owner_id=oid,
        current_state="qualification",
        niche_id_snapshot="generic",
        channel=None,
    )
    ok, reason = evaluate_lead_creation_gates(
        bot=bot,
        conversation=conv,
        collected_data_json={"primary_need": "x", "phone": "+1555"},
        funnel_state_override="closing",
    )
    assert ok is True
    assert reason is None


def test_capture_skips_when_owner_missing_sync() -> None:
    asyncio.run(_run_skip_owner())


async def _run_skip_owner() -> None:
    bot = SimpleNamespace(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        goal_type="sales",
        niche_id="generic",
        name="B",
    )
    conv = SimpleNamespace(
        id=uuid.uuid4(),
        bot_id=bot.id,
        owner_id=bot.owner_id,
        current_state="closing",
        niche_id_snapshot="generic",
        channel="web_chat",
    )
    collected: dict[str, object] = {"primary_need": "x", "phone": "+1"}
    lr = MagicMock(spec=LeadRepository)
    out = await run_sales_lead_capture_after_pipeline(
        lead_repo=lr,
        bot=bot,
        owner_user=None,
        conversation=conv,
        collected=collected,
        next_state=ConversationFlowState.closing,
        routing_intent=ConversationDetectedIntent.sales_interest,
        last_user_message="ok",
    )
    assert out.created_new_lead is False
    lr.get_lead_by_conversation_id.assert_not_called()
