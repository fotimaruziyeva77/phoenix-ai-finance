"""Unit tests for web widget visitor session key normalization (no database)."""

from __future__ import annotations

import uuid

import pytest
from app.lib.web_widget_visitor_session import (
    normalize_or_generate_visitor_session_key,
    sanitize_visitor_client_hint,
)


def test_normalize_accepts_uuid_string() -> None:
    u = uuid.uuid4()
    assert normalize_or_generate_visitor_session_key(str(u)) == str(u)


def test_normalize_accepts_urlsafe_token() -> None:
    s = "a" * 16
    assert normalize_or_generate_visitor_session_key(s) == s


def test_normalize_rejects_short_token() -> None:
    with pytest.raises(ValueError):
        normalize_or_generate_visitor_session_key("short")


def test_normalize_generates_when_blank() -> None:
    k = normalize_or_generate_visitor_session_key(None)
    assert len(k) >= 16
    assert "@" not in k
    assert " " not in k


def test_sanitize_hint_strips_and_truncates() -> None:
    assert sanitize_visitor_client_hint("  x  ") == "x"
    assert sanitize_visitor_client_hint(None) is None
    long = "a" * 200
    assert len(sanitize_visitor_client_hint(long) or "") == 128
