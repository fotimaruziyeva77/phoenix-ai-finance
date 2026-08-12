"""Verify consulting bots are now eligible for CRM lead capture (alongside sales)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.services.lead_creation_service import evaluate_lead_creation_gates


def _bot(*, owner_id: uuid.UUID, goal_type: str = "sales") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        owner_id=owner_id,
        goal_type=goal_type,
        niche_id="generic",
    )


def _conv(*, owner_id: uuid.UUID, bot_id: uuid.UUID, state: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        owner_id=owner_id,
        bot_id=bot_id,
        current_state=state,
        niche_id_snapshot=None,
    )


def test_consulting_bot_eligible_at_closing() -> None:
    oid = uuid.uuid4()
    bot = _bot(owner_id=oid, goal_type="consulting")
    conv = _conv(owner_id=oid, bot_id=bot.id, state="closing")
    ok, reason = evaluate_lead_creation_gates(
        bot=bot,
        conversation=conv,
        collected_data_json={"primary_need": "strategy review", "phone": "+998901234567"},
    )
    assert ok is True
    assert reason is None


def test_support_bot_still_rejected() -> None:
    oid = uuid.uuid4()
    bot = _bot(owner_id=oid, goal_type="support")
    conv = _conv(owner_id=oid, bot_id=bot.id, state="closing")
    ok, reason = evaluate_lead_creation_gates(
        bot=bot,
        conversation=conv,
        collected_data_json={"primary_need": "help", "phone": "+998901234567"},
    )
    assert ok is False
    assert reason == "skipped_not_sales_bot"


def test_faq_bot_still_rejected() -> None:
    oid = uuid.uuid4()
    bot = _bot(owner_id=oid, goal_type="faq")
    conv = _conv(owner_id=oid, bot_id=bot.id, state="closing")
    ok, reason = evaluate_lead_creation_gates(
        bot=bot,
        conversation=conv,
        collected_data_json={"primary_need": "info", "phone": "+998901234567"},
    )
    assert ok is False
    assert reason == "skipped_not_sales_bot"


def test_sales_bot_still_eligible() -> None:
    oid = uuid.uuid4()
    bot = _bot(owner_id=oid, goal_type="sales")
    conv = _conv(owner_id=oid, bot_id=bot.id, state="closing")
    ok, _ = evaluate_lead_creation_gates(
        bot=bot,
        conversation=conv,
        collected_data_json={"primary_need": "buy widget", "phone": "+998901234567"},
    )
    assert ok is True
