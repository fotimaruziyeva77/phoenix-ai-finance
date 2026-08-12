"""Unit tests for public widget bootstrap hostname allowlist (no database)."""

from __future__ import annotations

import pytest
from app.lib.widget_allowed_domains import (
    extract_hostname_from_origin_or_referer,
    normalize_allowed_domains,
    normalize_allowlist_entry_for_storage,
    request_hostname_matches_allowlist,
)
from app.lib.widget_origin_policy import WidgetOriginPolicyOptions, widget_request_origin_allowed


def test_empty_allowlist_allows_any_hostname_including_none() -> None:
    assert request_hostname_matches_allowlist(None, []) is True
    assert request_hostname_matches_allowlist("any.example", []) is True


def test_nonempty_allowlist_requires_exact_normalized_host() -> None:
    allowed = ["www.example.com", "partner.org"]
    assert request_hostname_matches_allowlist("www.example.com", allowed) is True
    assert request_hostname_matches_allowlist("WWW.EXAMPLE.COM.", allowed) is True
    assert request_hostname_matches_allowlist(None, allowed) is False
    assert request_hostname_matches_allowlist("evil.com", allowed) is False
    assert request_hostname_matches_allowlist("sub.www.example.com", allowed) is False


def test_allowlist_wildcard_subdomain_pattern() -> None:
    allowed = ["*.embed.example"]
    assert request_hostname_matches_allowlist("app.embed.example", allowed) is True
    assert request_hostname_matches_allowlist("embed.example", allowed) is False


def test_allowlist_leading_dot_matches_apex_and_subdomains() -> None:
    allowed = [".customer.test"]
    assert request_hostname_matches_allowlist("customer.test", allowed) is True
    assert request_hostname_matches_allowlist("www.customer.test", allowed) is True


def test_loopback_equivalent_respects_options() -> None:
    allowed = ["localhost"]
    assert request_hostname_matches_allowlist("127.0.0.1", allowed) is True
    opt = WidgetOriginPolicyOptions(loopback_aliases_equivalent=False)
    assert request_hostname_matches_allowlist("127.0.0.1", allowed, options=opt) is False


def test_extract_hostname_prefers_origin_over_referer() -> None:
    assert (
        extract_hostname_from_origin_or_referer("https://first.com", "https://second.com/page")
        == "first.com"
    )


def test_extract_hostname_uses_referer_when_origin_null_string() -> None:
    assert (
        extract_hostname_from_origin_or_referer("null", "https://ref.example/path")
        == "ref.example"
    )


def test_extract_hostname_returns_none_when_missing() -> None:
    assert extract_hostname_from_origin_or_referer(None, None) is None


def test_normalize_storage_preserves_wildcard_and_leading_dot() -> None:
    assert normalize_allowlist_entry_for_storage(" *.Example.COM ") == "*.example.com"
    assert normalize_allowlist_entry_for_storage(".Example.COM") == ".example.com"


def test_normalize_rejects_overbroad_wildcard_suffix() -> None:
    with pytest.raises(ValueError):
        normalize_allowed_domains(["*.com"])
    with pytest.raises(ValueError):
        normalize_allowed_domains([".com"])


def test_normalize_rejects_wildcards_when_disabled() -> None:
    with pytest.raises(ValueError, match="wildcard allowlist patterns"):
        normalize_allowed_domains(["*.example.com"], allow_wildcard_patterns=False)
    with pytest.raises(ValueError, match="wildcard allowlist patterns"):
        normalize_allowed_domains([".example.com"], allow_wildcard_patterns=False)
    assert normalize_allowed_domains(["www.example.com"], allow_wildcard_patterns=False) == ["www.example.com"]


@pytest.mark.parametrize(
    ("origin", "referer", "expected"),
    [
        (None, None, None),
        ("", None, None),
        ("null", None, None),
        ("https://", None, None),
        ("https:///", None, None),
        ("not-a-scheme-just-labels", None, "not-a-scheme-just-labels"),
        ("https://only.one", None, "only.one"),
        ("null", "https://from.referer/page", "from.referer"),
    ],
)
def test_extract_hostname_malformed_or_edge_origins(
    origin: str | None,
    referer: str | None,
    expected: str | None,
) -> None:
    assert extract_hostname_from_origin_or_referer(origin, referer) == expected


def test_widget_policy_never_raises_on_odd_hosts() -> None:
    allowed = ["safe.allowlist.test"]
    for raw in ("", "com", "127", "a" * 500):
        _ = widget_request_origin_allowed(raw if raw else None, allowed)


def test_normalize_widget_hostname_bracket_ipv6_and_trailing_dot() -> None:
    from app.lib.widget_allowed_domains import normalize_widget_hostname

    assert normalize_widget_hostname("http://[::1]:8080") == "::1"
    assert normalize_widget_hostname("HTTPS://WWW.X.EXAMPLE./") == "www.x.example"
