"""Unit tests for public widget key generation (no database)."""

from __future__ import annotations

import string

from app.lib.public_widget_key import generate_public_widget_key

_ALLOWED = frozenset(string.ascii_letters + string.digits + "-_")


def test_generate_public_widget_key_urlsafe_and_sufficient_entropy() -> None:
    for _ in range(50):
        key = generate_public_widget_key()
        assert len(key) >= 40
        assert all(c in _ALLOWED for c in key)


def test_generate_public_widget_key_many_samples_are_unique() -> None:
    keys = {generate_public_widget_key() for _ in range(500)}
    assert len(keys) == 500
