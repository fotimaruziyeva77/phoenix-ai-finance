"""Unit tests for :mod:`app.core.public_widget_channel_events` (no HTTP)."""

from __future__ import annotations

from app.core.public_widget_abuse import widget_key_digest
from app.core.public_widget_channel_events import (
    is_public_widget_chat_path,
    public_widget_key_digest_from_path,
    visitor_session_digest,
)


def test_public_widget_key_digest_from_path_matches_widget_key_digest() -> None:
    key = "test_public_widget_key_12345"
    path = f"/api/v1/public/widget/{key}/bootstrap"
    assert public_widget_key_digest_from_path(path) == widget_key_digest(key)
    assert public_widget_key_digest_from_path(f"/api/v1/public/widget/{key}/chat") == widget_key_digest(key)


def test_public_widget_key_digest_from_path_rejects_non_widget_paths() -> None:
    assert public_widget_key_digest_from_path("/api/v1/bots") is None
    assert public_widget_key_digest_from_path("") is None


def test_is_public_widget_chat_path() -> None:
    assert is_public_widget_chat_path("/api/v1/public/widget/k/chat") is True
    assert is_public_widget_chat_path("/api/v1/public/widget/k/chat/") is True
    assert is_public_widget_chat_path("/api/v1/public/widget/k/bootstrap") is False
    assert is_public_widget_chat_path("/api/v1/bots") is False


def test_visitor_session_digest_short_key_omitted() -> None:
    assert visitor_session_digest(None) is None
    assert visitor_session_digest("") is None
    assert visitor_session_digest("short") is None


def test_visitor_session_digest_long_key_stable() -> None:
    k = "a" * 20
    d1 = visitor_session_digest(k)
    d2 = visitor_session_digest(k)
    assert d1 == d2
    assert len(d1 or "") == 12
