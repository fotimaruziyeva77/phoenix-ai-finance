"""Tests for :mod:`app.services.lead_pipeline_policy`."""

from __future__ import annotations

import pytest
from app.services.lead_pipeline_policy import (
    LeadStatusTransitionError,
    validate_lead_status_change,
)


@pytest.mark.parametrize(
    ("from_s", "to_s"),
    [
        ("new", "contacted"),
        ("proposal", "new"),
        ("qualified", "won"),
        ("new", "lost"),
    ],
)
def test_open_and_into_terminal_allowed(from_s: str, to_s: str) -> None:
    validate_lead_status_change(from_s, to_s)


def test_no_op_always_allowed() -> None:
    validate_lead_status_change("won", "won")
    validate_lead_status_change("lost", "lost")


def test_terminal_cannot_move_to_open() -> None:
    with pytest.raises(LeadStatusTransitionError) as excinfo:
        validate_lead_status_change("won", "contacted")
    assert excinfo.value.from_status == "won"
    assert excinfo.value.to_status == "contacted"


def test_terminal_to_other_terminal_blocked() -> None:
    with pytest.raises(LeadStatusTransitionError):
        validate_lead_status_change("won", "lost")
