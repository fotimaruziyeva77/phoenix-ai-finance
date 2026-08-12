"""Unit tests for ``app.core.public_widget_abuse`` (no HTTP stack)."""

from __future__ import annotations

import pytest
from app.core.config import Settings
from app.core.public_widget_abuse import (
    enforce_public_widget_chat_turn,
    reset_public_widget_abuse_memory_for_tests,
    widget_key_digest,
)
from app.core.rate_limit import InMemorySlidingWindowLimiter
from fastapi import HTTPException
from starlette.requests import Request


def _http_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
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


@pytest.mark.asyncio
async def test_widget_key_digest_is_stable_hex_prefix() -> None:
    d = widget_key_digest("  my-key  ")
    assert len(d) == 16
    assert d == widget_key_digest("my-key")


@pytest.mark.asyncio
async def test_message_over_max_length_returns_400() -> None:
    settings = _abuse_settings(public_widget_abuse_max_message_chars=50)
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    long_text = "a" * 51
    with pytest.raises(HTTPException) as exc:
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="k",
            message_text=long_text,
            visitor_session_key=None,
            limiter=limiter,
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_session_burst_blocks_after_limit() -> None:
    settings = _abuse_settings(public_widget_abuse_session_burst_per_minute=3)
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    for i in range(3):
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="widget-a",
            message_text=f"msg {i}",
            visitor_session_key="visitor-session-key-16chars",
            limiter=limiter,
        )
    with pytest.raises(HTTPException) as exc:
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="widget-a",
            message_text="fourth",
            visitor_session_key="visitor-session-key-16chars",
            limiter=limiter,
        )
    assert exc.value.status_code == 429
    assert exc.value.headers and exc.value.headers.get("Retry-After") == "60"


@pytest.mark.asyncio
async def test_identical_message_burst_in_window() -> None:
    settings = _abuse_settings(
        public_widget_abuse_session_burst_per_minute=0,
        public_widget_abuse_identical_total_per_window=3,
        public_widget_abuse_max_consecutive_identical=0,
    )
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    for _ in range(2):
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="w",
            message_text="SPAM   SPAM",
            visitor_session_key="k" * 16,
            limiter=limiter,
        )
    with pytest.raises(HTTPException) as exc:
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="w",
            message_text="SPAM SPAM",
            visitor_session_key="k" * 16,
            limiter=limiter,
        )
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_consecutive_identical_blocks() -> None:
    settings = _abuse_settings(
        public_widget_abuse_session_burst_per_minute=0,
        public_widget_abuse_identical_total_per_window=0,
        public_widget_abuse_max_consecutive_identical=3,
    )
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    await enforce_public_widget_chat_turn(
        request=req,
        settings=settings,
        public_widget_key="w",
        message_text="x",
        visitor_session_key="z" * 16,
        limiter=limiter,
    )
    await enforce_public_widget_chat_turn(
        request=req,
        settings=settings,
        public_widget_key="w",
        message_text="x",
        visitor_session_key="z" * 16,
        limiter=limiter,
    )
    with pytest.raises(HTTPException) as exc:
        await enforce_public_widget_chat_turn(
            request=req,
            settings=settings,
            public_widget_key="w",
            message_text="x",
            visitor_session_key="z" * 16,
            limiter=limiter,
        )
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_abuse_disabled_skips_heuristics() -> None:
    settings = _abuse_settings(
        public_widget_abuse_enabled=False,
        public_widget_abuse_max_message_chars=10,
    )
    limiter = InMemorySlidingWindowLimiter()
    req = _http_request()
    await enforce_public_widget_chat_turn(
        request=req,
        settings=settings,
        public_widget_key="w",
        message_text="x" * 500,
        visitor_session_key=None,
        limiter=limiter,
    )
