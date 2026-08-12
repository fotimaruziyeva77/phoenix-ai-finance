"""
Safeguard and edge-case tests for public widget anti-abuse.

Covers: spam throttling, long-message handling, normal use, no response leaks,
session-scoped limits, and HTTP error envelope behavior.
"""

from __future__ import annotations

import json
import uuid

import pytest
from app.core.config import Settings
from app.core.exception_handlers import http_exception_handler
from app.core.public_widget_abuse import (
    enforce_public_widget_chat_turn,
    reset_public_widget_abuse_memory_for_tests,
    widget_key_digest,
)
from app.core.rate_limit import InMemorySlidingWindowLimiter
from fastapi import HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request


def _http_request(*, path: str = "/") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [],
            "client": ("198.51.100.42", 44444),
        }
    )


def _abuse_settings(**overrides: object) -> Settings:
    base = dict(
        rate_limiting_enabled=True,
        public_widget_abuse_enabled=True,
        trust_forwarded_for=False,
        public_widget_abuse_session_burst_per_minute=20,
        public_widget_abuse_identical_total_per_window=20,
        public_widget_abuse_identical_window_seconds=300.0,
        public_widget_abuse_max_consecutive_identical=20,
        public_widget_abuse_max_message_chars=0,
    )
    base.update(overrides)
    return Settings.model_validate(base)


@pytest.fixture(autouse=True)
def _reset_abuse_memory() -> None:
    reset_public_widget_abuse_memory_for_tests()
    yield
    reset_public_widget_abuse_memory_for_tests()


# --- Checklist 1: spam throttled safely ---


@pytest.mark.asyncio
async def test_safeguard_repeated_identical_spam_throttled_after_threshold() -> None:
    settings = _abuse_settings(
        public_widget_abuse_session_burst_per_minute=0,
        public_widget_abuse_identical_total_per_window=4,
        public_widget_abuse_max_consecutive_identical=0,
    )
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    for _ in range(3):
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="wk",
            message_text="buy now cheap",
            visitor_session_key="s" * 16,
            limiter=limiter,
        )
    with pytest.raises(HTTPException) as exc:
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="wk",
            message_text="buy now cheap",
            visitor_session_key="s" * 16,
            limiter=limiter,
        )
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_safeguard_consecutive_spam_throttled() -> None:
    settings = _abuse_settings(
        public_widget_abuse_session_burst_per_minute=0,
        public_widget_abuse_identical_total_per_window=0,
        public_widget_abuse_max_consecutive_identical=4,
    )
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    for _ in range(3):
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="wk",
            message_text="ping",
            visitor_session_key="uuuuuuuuuuuuuuuu",
            limiter=limiter,
        )
    with pytest.raises(HTTPException) as exc:
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="wk",
            message_text="ping",
            visitor_session_key="uuuuuuuuuuuuuuuu",
            limiter=limiter,
        )
    assert exc.value.status_code == 429


# --- Checklist 2: long messages ---


@pytest.mark.asyncio
async def test_safeguard_message_at_max_length_allowed() -> None:
    settings = _abuse_settings(public_widget_abuse_max_message_chars=500)
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    text = "z" * 500
    await enforce_public_widget_chat_turn(
        request=req,
        settings=settings,
        public_widget_key="k",
        message_text=text,
        visitor_session_key="v" * 16,
        limiter=limiter,
    )


@pytest.mark.asyncio
async def test_safeguard_message_one_char_over_max_blocked() -> None:
    settings = _abuse_settings(public_widget_abuse_max_message_chars=500)
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    with pytest.raises(HTTPException) as exc:
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="k",
            message_text="y" * 501,
            visitor_session_key="v" * 16,
            limiter=limiter,
        )
    assert exc.value.status_code == 400


# --- Checklist 3: valid normal use ---


@pytest.mark.asyncio
async def test_safeguard_normal_distinct_messages_under_burst_cap() -> None:
    settings = _abuse_settings(public_widget_abuse_session_burst_per_minute=10)
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    for i in range(8):
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="widget",
            message_text=f"Question {i}: what about topic {uuid.uuid4().hex[:8]}?",
            visitor_session_key="n" * 16,
            limiter=limiter,
        )


@pytest.mark.asyncio
async def test_safeguard_consecutive_streak_resets_when_message_changes() -> None:
    settings = _abuse_settings(
        public_widget_abuse_session_burst_per_minute=0,
        public_widget_abuse_identical_total_per_window=0,
        public_widget_abuse_max_consecutive_identical=3,
    )
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    vk = "r" * 16
    await enforce_public_widget_chat_turn(
        request=req, settings=settings, public_widget_key="w", message_text="a", visitor_session_key=vk, limiter=limiter
    )
    await enforce_public_widget_chat_turn(
        request=req, settings=settings, public_widget_key="w", message_text="a", visitor_session_key=vk, limiter=limiter
    )
    await enforce_public_widget_chat_turn(
        request=req, settings=settings, public_widget_key="w", message_text="b", visitor_session_key=vk, limiter=limiter
    )
    await enforce_public_widget_chat_turn(
        request=req, settings=settings, public_widget_key="w", message_text="a", visitor_session_key=vk, limiter=limiter
    )
    await enforce_public_widget_chat_turn(
        request=req, settings=settings, public_widget_key="w", message_text="a", visitor_session_key=vk, limiter=limiter
    )


@pytest.mark.asyncio
async def test_safeguard_whitespace_normalization_treats_equivalent_text_as_identical() -> None:
    settings = _abuse_settings(
        public_widget_abuse_session_burst_per_minute=0,
        public_widget_abuse_identical_total_per_window=3,
        public_widget_abuse_max_consecutive_identical=0,
    )
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    vk = "w" * 16
    await enforce_public_widget_chat_turn(
        request=req,
        settings=settings,
        public_widget_key="w",
        message_text="hello\n\nworld",
        visitor_session_key=vk,
        limiter=limiter,
    )
    await enforce_public_widget_chat_turn(
        request=req,
        settings=settings,
        public_widget_key="w",
        message_text="hello   world",
        visitor_session_key=vk,
        limiter=limiter,
    )
    with pytest.raises(HTTPException) as exc:
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="w",
            message_text="hello world",
            visitor_session_key=vk,
            limiter=limiter,
        )
    assert exc.value.status_code == 429


# --- Checklist 4: no technical leak in client-facing errors ---

_FORBIDDEN_LEAK_SUBSTRINGS = (
    "session_burst",
    "identical_message",
    "consecutive_identical",
    "message_too_long",
    "widget_key_digest",
    "fingerprint",
    "pub_wg_sess",
    "idup:",
    "sha256",
    "traceback",
    "File ",
)


@pytest.mark.asyncio
async def test_safeguard_throttle_http_envelope_has_no_internal_leaks() -> None:
    req = _http_request(path="/api/v1/public/widget/x/chat")
    exc = StarletteHTTPException(
        status_code=429,
        detail="Too many messages. Please try again shortly.",
        headers={"Retry-After": "60"},
    )
    resp = await http_exception_handler(req, exc)
    raw = resp.body.decode()
    lower = raw.lower()
    for bad in _FORBIDDEN_LEAK_SUBSTRINGS:
        assert bad.lower() not in lower, f"leaked {bad!r} in {raw!r}"
    payload = json.loads(raw)
    err = payload["error"]
    assert err["code"] == "rate_limit_exceeded"
    assert err.get("category") is None
    assert err["message"] == "Too many messages. Please try again shortly."
    assert resp.headers.get("retry-after") == "60"


@pytest.mark.asyncio
async def test_safeguard_long_message_http_envelope_has_no_internal_leaks() -> None:
    req = _http_request(path="/api/v1/public/widget/x/chat")
    exc = StarletteHTTPException(
        status_code=400,
        detail="Message is too long for this chat. Please shorten your text.",
    )
    resp = await http_exception_handler(req, exc)
    raw = resp.body.decode().lower()
    for bad in _FORBIDDEN_LEAK_SUBSTRINGS:
        assert bad.lower() not in raw


# --- Checklist 5: session-based rate limiting ---


@pytest.mark.asyncio
async def test_edge_two_distinct_sessions_same_ip_independent_burst_budgets() -> None:
    settings = _abuse_settings(public_widget_abuse_session_burst_per_minute=2)
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    wk = "same-widget-key-xxxxxxxx"
    for i in range(2):
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key=wk,
            message_text=f"a{i}",
            visitor_session_key="A" * 16,
            limiter=limiter,
        )
    for j in range(2):
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key=wk,
            message_text=f"b{j}",
            visitor_session_key="B" * 16,
            limiter=limiter,
        )


@pytest.mark.asyncio
async def test_edge_pre_session_visitors_share_ip_bucket() -> None:
    """No visitor_session_key yet: bucket is ``i:<ip>`` so same client shares one cap."""
    settings = _abuse_settings(public_widget_abuse_session_burst_per_minute=2)
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    for i in range(2):
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="widget-one",
            message_text=f"n{i}",
            visitor_session_key=None,
            limiter=limiter,
        )
    with pytest.raises(HTTPException):
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="widget-one",
            message_text="blocked",
            visitor_session_key=None,
            limiter=limiter,
        )


@pytest.mark.asyncio
async def test_edge_different_widgets_isolate_session_burst() -> None:
    settings = _abuse_settings(public_widget_abuse_session_burst_per_minute=2)
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    vk = "shared-visitor-16"
    for _ in range(2):
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="widget-aaaaaaaaaa",
            message_text="x",
            visitor_session_key=vk,
            limiter=limiter,
        )
    for _ in range(2):
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="widget-bbbbbbbbbb",
            message_text="y",
            visitor_session_key=vk,
            limiter=limiter,
        )


@pytest.mark.asyncio
async def test_edge_session_burst_zero_disables_sliding_window() -> None:
    settings = _abuse_settings(
        public_widget_abuse_session_burst_per_minute=0,
        public_widget_abuse_identical_total_per_window=0,
        public_widget_abuse_max_consecutive_identical=0,
    )
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    for _ in range(25):
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="w",
            message_text=f"uniq-{uuid.uuid4()}",
            visitor_session_key="k" * 16,
            limiter=limiter,
        )


@pytest.mark.asyncio
async def test_edge_rate_limiting_disabled_skips_all_abuse_heuristics() -> None:
    settings = _abuse_settings(
        rate_limiting_enabled=False,
        public_widget_abuse_max_message_chars=5,
        public_widget_abuse_session_burst_per_minute=1,
    )
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    await enforce_public_widget_chat_turn(
        request=req,
        settings=settings,
        public_widget_key="w",
        message_text="x" * 100,
        visitor_session_key="k" * 16,
        limiter=limiter,
    )
    await enforce_public_widget_chat_turn(
        request=req,
        settings=settings,
        public_widget_key="w",
        message_text="y" * 100,
        visitor_session_key="k" * 16,
        limiter=limiter,
    )


@pytest.mark.asyncio
async def test_edge_widget_digest_stable_for_session_keys() -> None:
    d1 = widget_key_digest("abc")
    d2 = widget_key_digest("abc")
    assert d1 == d2
    assert d1 != widget_key_digest("abd")
