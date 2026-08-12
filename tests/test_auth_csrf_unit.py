"""CSRF double-submit helpers (no HTTP server)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from app.core.auth_cookies import csrf_header_matches_cookie


@pytest.fixture
def settings() -> MagicMock:
    s = MagicMock()
    s.auth_csrf_cookie_name = "bf_csrf"
    s.auth_csrf_header_name = "X-CSRF-Token"
    return s


def test_csrf_matches_when_header_equals_cookie(settings: MagicMock) -> None:
    req = MagicMock()
    req.cookies = {"bf_csrf": "abc"}
    req.headers = {"X-CSRF-Token": "abc"}
    assert csrf_header_matches_cookie(req, settings) is True


def test_csrf_rejects_mismatch(settings: MagicMock) -> None:
    req = MagicMock()
    req.cookies = {"bf_csrf": "abc"}
    req.headers = {"X-CSRF-Token": "xyz"}
    assert csrf_header_matches_cookie(req, settings) is False


def test_csrf_rejects_missing_header(settings: MagicMock) -> None:
    req = MagicMock()
    req.cookies = {"bf_csrf": "abc"}
    req.headers = {}
    assert csrf_header_matches_cookie(req, settings) is False
