"""Pure-function tests for :mod:`app.services.lead_safeguards`."""

from __future__ import annotations

import pytest
from app.services.lead_safeguards import (
    assess_lead_payload_quality,
    normalize_phone_digits,
    phone_correlation_key,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, ""),
        ("", ""),
        ("+1 (555) 010-2030", "15550102030"),
        ("abc", ""),
    ],
)
def test_normalize_phone_digits(raw: str | None, expected: str) -> None:
    assert normalize_phone_digits(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected_key"),
    [
        ("+1", None),
        ("123456", None),
        ("1234567", "1234567"),
        ("+44 20 7946 0958", "442079460958"),
    ],
)
def test_phone_correlation_key(raw: str | None, expected_key: str | None) -> None:
    assert phone_correlation_key(raw) == expected_key


def test_assess_quality_allows_when_any_signal_strong() -> None:
    assert assess_lead_payload_quality(summary="", name=None, lead_score=15) == (True, None)
    assert assess_lead_payload_quality(summary="x" * 8, name=None, lead_score=0) == (True, None)
    assert assess_lead_payload_quality(summary="no", name="Pat", lead_score=0) == (True, None)


def test_assess_quality_skips_only_when_all_weak() -> None:
    ok, reason = assess_lead_payload_quality(summary="bad", name="  ", lead_score=10)
    assert ok is False
    assert reason == "skipped_low_quality_signals"


@pytest.mark.parametrize(
    ("summary", "name", "score", "expect_ok"),
    [
        ("x" * 7, None, 14, False),
        ("x" * 7, "Jo", 14, False),
        ("x" * 7, "Joe", 14, True),
        ("x" * 8, None, 14, True),
        ("", None, 14, False),
        ("", None, 15, True),
        ("x" * 7, None, 15, True),
    ],
)
def test_assess_quality_threshold_combinations(
    summary: str,
    name: str | None,
    score: int,
    expect_ok: bool,
) -> None:
    ok, reason = assess_lead_payload_quality(summary=summary, name=name, lead_score=score)
    if expect_ok:
        assert ok is True
        assert reason is None
    else:
        assert ok is False
        assert reason == "skipped_low_quality_signals"
