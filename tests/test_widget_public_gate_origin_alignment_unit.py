"""
No-DB alignment: the public gate must mirror :func:`widget_request_origin_allowed`
(the same function bootstrap and chat call).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from app.lib.widget_allowed_domains import extract_hostname_from_origin_or_referer
from app.lib.widget_origin_policy import WidgetOriginPolicyOptions, widget_request_origin_allowed
from app.services.widget_bootstrap_exceptions import (
    WidgetBootstrapDisabledError,
    WidgetBootstrapOriginForbiddenError,
)
from app.services.widget_public_gate import enforce_public_widget_origin_and_enabled


def _fake_wc(*, enabled: bool = True, domains: list[str]) -> SimpleNamespace:
    return SimpleNamespace(is_enabled=enabled, allowed_domains_json=domains)


@pytest.mark.parametrize(
    ("origin", "referer", "domains", "expect_allowed"),
    [
        ("https://ok.test", None, ["ok.test"], True),
        ("https://evil.test", None, ["ok.test"], False),
        (None, None, ["ok.test"], False),
        ("https://app.sub.test", None, ["*.sub.test"], True),
        ("https://sub.test", None, ["*.sub.test"], False),
        ("http://127.0.0.1:3000", None, ["localhost"], True),
    ],
)
def test_gate_decision_matches_policy_module(
    origin: str | None,
    referer: str | None,
    domains: list[str],
    expect_allowed: bool,
) -> None:
    wc = _fake_wc(domains=domains)
    policy = WidgetOriginPolicyOptions()
    host = extract_hostname_from_origin_or_referer(origin, referer)
    policy_ok = widget_request_origin_allowed(host, list(domains), options=policy)
    assert policy_ok is expect_allowed

    if expect_allowed:
        enforce_public_widget_origin_and_enabled(
            wc,
            origin_header=origin,
            referer_header=referer,
            origin_policy=policy,
        )
    else:
        with pytest.raises(WidgetBootstrapOriginForbiddenError):
            enforce_public_widget_origin_and_enabled(
                wc,
                origin_header=origin,
                referer_header=referer,
                origin_policy=policy,
            )


def test_disabled_widget_raises_before_origin_check() -> None:
    wc = _fake_wc(enabled=False, domains=["any.test"])
    with pytest.raises(WidgetBootstrapDisabledError):
        enforce_public_widget_origin_and_enabled(
            wc,
            origin_header="https://any.test",
            referer_header=None,
        )


def test_loopback_option_propagates_through_gate() -> None:
    wc = _fake_wc(domains=["localhost"])
    strict = WidgetOriginPolicyOptions(loopback_aliases_equivalent=False)
    with pytest.raises(WidgetBootstrapOriginForbiddenError):
        enforce_public_widget_origin_and_enabled(
            wc,
            origin_header="http://127.0.0.1:3000",
            referer_header=None,
            origin_policy=strict,
        )


def test_empty_allowlist_deny_flag_matches_policy_module() -> None:
    policy = WidgetOriginPolicyOptions(deny_empty_allowlist=True)
    wc = _fake_wc(domains=[])
    host = extract_hostname_from_origin_or_referer("https://allowed-looking.test", None)
    assert widget_request_origin_allowed(host, [], options=policy) is False
    with pytest.raises(WidgetBootstrapOriginForbiddenError):
        enforce_public_widget_origin_and_enabled(
            wc,
            origin_header="https://allowed-looking.test",
            referer_header=None,
            origin_policy=policy,
        )
