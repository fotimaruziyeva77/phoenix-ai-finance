"""Unit tests for :mod:`app.lib.widget_origin_policy` (no HTTP, no DB)."""

from __future__ import annotations

import pytest
from app.lib.widget_origin_policy import WidgetOriginPolicyOptions, widget_request_origin_allowed


@pytest.mark.parametrize(
    ("req", "allowed", "expect"),
    [
        ("app.example.com", ["*.example.com"], True),
        ("deep.app.example.com", ["*.example.com"], True),
        ("example.com", ["*.example.com"], False),
        ("notexample.com", ["*.example.com"], False),
        ("example.com", [".example.com"], True),
        ("www.example.com", [".example.com"], True),
        ("a.b.example.com", [".example.com"], True),
        ("www.other.com", [".example.com"], False),
        ("www.example.com", ["www.example.com"], True),
    ],
)
def test_wildcard_and_leading_dot_patterns(req: str, allowed: list[str], expect: bool) -> None:
    assert widget_request_origin_allowed(req, allowed) is expect


def test_empty_allowlist_allows_even_missing_host_when_not_deny() -> None:
    assert widget_request_origin_allowed(None, []) is True
    assert widget_request_origin_allowed("anything", []) is True


def test_empty_allowlist_denies_when_deny_empty_flag() -> None:
    opt = WidgetOriginPolicyOptions(deny_empty_allowlist=True)
    assert widget_request_origin_allowed(None, [], options=opt) is False
    assert widget_request_origin_allowed("evil.com", [], options=opt) is False


def test_nonempty_allowlist_denies_missing_host() -> None:
    assert widget_request_origin_allowed(None, ["a.com"]) is False


def test_loopback_equivalent_default() -> None:
    assert widget_request_origin_allowed("127.0.0.1", ["localhost"]) is True
    assert widget_request_origin_allowed("localhost", ["127.0.0.1"]) is True
    assert widget_request_origin_allowed("[::1]", ["localhost"]) is True


def test_loopback_equivalent_disabled() -> None:
    opt = WidgetOriginPolicyOptions(loopback_aliases_equivalent=False)
    assert widget_request_origin_allowed("127.0.0.1", ["localhost"], options=opt) is False
    assert widget_request_origin_allowed("127.0.0.1", ["127.0.0.1"], options=opt) is True


def test_multiple_domains_or_match() -> None:
    allowed = ["partner.org", "*.customer.test", ".shared.io"]
    assert widget_request_origin_allowed("partner.org", allowed) is True
    assert widget_request_origin_allowed("x.customer.test", allowed) is True
    assert widget_request_origin_allowed("customer.test", allowed) is False
    assert widget_request_origin_allowed("app.shared.io", allowed) is True
    assert widget_request_origin_allowed("shared.io", allowed) is True
