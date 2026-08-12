"""Tests for :func:`app.integrations.telegram.lead_alert_message.format_new_lead_alert_message`."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.integrations.telegram.lead_alert_message import format_new_lead_alert_message
from app.integrations.telegram.lead_alert_types import NewLeadAlertPayload


def test_format_includes_core_fields() -> None:
    lid = uuid.uuid4()
    cap = datetime(2026, 4, 3, 14, 30, tzinfo=timezone.utc)
    p = NewLeadAlertPayload(
        lead_id=lid,
        bot_name="Sales Bot",
        niche_id="education",
        lead_temperature="hot",
        phone="+15551234567",
        summary="Wants calculus tutoring.",
        lead_score=88,
        captured_at=cap,
    )
    text = format_new_lead_alert_message(p)
    assert "Sales Bot" in text
    assert "education" in text
    assert "hot" in text
    assert "+15551234567" in text
    assert "88" in text
    assert "Wants calculus tutoring." in text
    assert str(lid) in text
    assert "2026-04-03" in text and "14:30:00" in text
    assert "Source: —" in text


def test_format_includes_source_channel_when_set() -> None:
    p = NewLeadAlertPayload(
        lead_id=uuid.uuid4(),
        bot_name="B",
        niche_id="n",
        lead_temperature=None,
        phone=None,
        summary="s",
        lead_score=None,
        captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source_channel="telegram",
    )
    text = format_new_lead_alert_message(p)
    assert "Source: telegram" in text


def test_format_truncates_for_telegram_limit() -> None:
    lid = uuid.uuid4()
    cap = datetime(2026, 1, 1, tzinfo=timezone.utc)
    huge = "x" * 5000
    p = NewLeadAlertPayload(
        lead_id=lid,
        bot_name="B",
        niche_id="n",
        lead_temperature="cold",
        phone=None,
        summary=huge,
        lead_score=None,
        captured_at=cap,
    )
    text = format_new_lead_alert_message(p)
    assert len(text) <= 4096
    assert "truncated" in text.lower()
