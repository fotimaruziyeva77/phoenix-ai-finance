"""Distributed rate limiting and widget abuse (shared Redis / fakeredis)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import redis.asyncio as redis
from fakeredis import FakeServer
from fakeredis.aioredis import FakeRedis
from fastapi import HTTPException

from app.api import deps as api_deps
from app.core.limiters.memory_sliding_window import InMemorySlidingWindowLimiter
from app.core.limiters.redis_sliding_window import RedisSlidingWindowLimiter
from app.core.public_widget_abuse import enforce_public_widget_chat_turn, reset_public_widget_abuse_memory_for_tests
from app.core.widget_abuse_redis import RedisWidgetStreakTracker


@pytest.mark.asyncio
async def test_sliding_window_shared_across_two_redis_clients() -> None:
    server = FakeServer()
    r1 = FakeRedis(server=server, decode_responses=True)
    r2 = FakeRedis(server=server, decode_responses=True)
    lim1 = RedisSlidingWindowLimiter(r1, key_prefix="itest:sw:")
    lim2 = RedisSlidingWindowLimiter(r2, key_prefix="itest:sw:")
    limit = 5
    for i in range(limit):
        o = await lim1.consume("same_ip", limit=limit, window_seconds=60.0)
        assert o.allowed, i
    blocked = await lim2.consume("same_ip", limit=limit, window_seconds=60.0)
    assert not blocked.allowed
    assert blocked.retry_after_seconds >= 1
    await r1.aclose()
    await r2.aclose()


@pytest.mark.asyncio
async def test_widget_streak_shared_across_two_redis_clients() -> None:
    server = FakeServer()
    r1 = FakeRedis(server=server, decode_responses=True)
    r2 = FakeRedis(server=server, decode_responses=True)
    t1 = RedisWidgetStreakTracker(r1, key_prefix="itest:str:")
    t2 = RedisWidgetStreakTracker(r2, key_prefix="itest:str:")
    fp = "cafef00d"
    lim = 6
    for _ in range(5):
        o = await t1.check_and_record("sk", fp, limit=lim, ttl_seconds=600)
        assert o.allowed
    o_block = await t2.check_and_record("sk", fp, limit=lim, ttl_seconds=600)
    assert not o_block.allowed
    assert o_block.retry_after_seconds >= 1
    await r1.aclose()
    await r2.aclose()


@pytest.mark.asyncio
async def test_auth_rate_limit_redis_error_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_deps, "client_ip", lambda *_a, **_kw: "192.0.2.10")

    class _Down:
        async def consume(self, *_a, **_kw):
            raise redis.ConnectionError("redis down")

    settings = MagicMock()
    settings.rate_limiting_enabled = True
    settings.rate_limit_auth_fail_closed_on_redis_error = True
    settings.trust_forwarded_for = False

    with pytest.raises(HTTPException) as ei:
        await api_deps._enforce_rate_limit(
            MagicMock(),
            settings,
            _Down(),
            prefix="auth_login",
            limit_per_minute=10,
            endpoint_scope="auth",
        )
    assert ei.value.status_code == 503


@pytest.mark.asyncio
async def test_auth_rate_limit_redis_error_allow_when_not_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_deps, "client_ip", lambda *_a, **_kw: "192.0.2.11")

    class _Down:
        async def consume(self, *_a, **_kw):
            raise redis.ConnectionError("redis down")

    settings = MagicMock()
    settings.rate_limiting_enabled = True
    settings.rate_limit_auth_fail_closed_on_redis_error = False
    settings.trust_forwarded_for = False

    await api_deps._enforce_rate_limit(
        MagicMock(),
        settings,
        _Down(),
        prefix="auth_refresh",
        limit_per_minute=10,
        endpoint_scope="auth",
    )


@pytest.mark.asyncio
async def test_public_widget_rate_limit_redis_error_fail_open(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_deps, "client_ip", lambda *_a, **_kw: "192.0.2.20")
    monkeypatch.setattr(api_deps, "emit_public_widget_channel_event", lambda **kwargs: None)

    class _Down:
        async def consume(self, *_a, **_kw):
            raise redis.ConnectionError("redis down")

    settings = MagicMock()
    settings.rate_limiting_enabled = True
    settings.rate_limit_public_fail_open_on_redis_error = True
    settings.trust_forwarded_for = False

    await api_deps._enforce_public_widget_rate_limit(
        MagicMock(),
        settings,
        _Down(),
        prefix="pub_widget_chat",
        limit_per_minute=5,
        throttle_kind="rate_limit_chat",
        digest="abc12",
        detail="Too many messages.",
    )


@pytest.mark.asyncio
async def test_public_widget_rate_limit_redis_error_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_deps, "client_ip", lambda *_a, **_kw: "192.0.2.21")

    class _Down:
        async def consume(self, *_a, **_kw):
            raise redis.ConnectionError("redis down")

    settings = MagicMock()
    settings.rate_limiting_enabled = True
    settings.rate_limit_public_fail_open_on_redis_error = False
    settings.trust_forwarded_for = False

    with pytest.raises(HTTPException) as ei:
        await api_deps._enforce_public_widget_rate_limit(
            MagicMock(),
            settings,
            _Down(),
            prefix="pub_widget_boot",
            limit_per_minute=3,
            throttle_kind="rate_limit_bootstrap",
            digest="def34",
            detail="Too many requests.",
        )
    assert ei.value.status_code == 503


@pytest.mark.asyncio
async def test_public_widget_429_sets_retry_after_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_deps, "client_ip", lambda *_a, **_kw: "192.0.2.30")
    monkeypatch.setattr(api_deps, "emit_public_widget_channel_event", lambda **kwargs: None)

    settings = MagicMock()
    settings.rate_limiting_enabled = True
    settings.trust_forwarded_for = False
    settings.rate_limit_public_fail_open_on_redis_error = True

    lim = InMemorySlidingWindowLimiter()
    await api_deps._enforce_public_widget_rate_limit(
        MagicMock(),
        settings,
        lim,
        prefix="pub_retry",
        limit_per_minute=2,
        throttle_kind="rate_limit_chat",
        digest="zzz",
        detail="Too many.",
    )
    await api_deps._enforce_public_widget_rate_limit(
        MagicMock(),
        settings,
        lim,
        prefix="pub_retry",
        limit_per_minute=2,
        throttle_kind="rate_limit_chat",
        digest="zzz",
        detail="Too many.",
    )
    with pytest.raises(HTTPException) as ei:
        await api_deps._enforce_public_widget_rate_limit(
            MagicMock(),
            settings,
            lim,
            prefix="pub_retry",
            limit_per_minute=2,
            throttle_kind="rate_limit_chat",
            digest="zzz",
            detail="Too many.",
        )
    assert ei.value.status_code == 429
    assert ei.value.headers is not None
    assert "Retry-After" in ei.value.headers


@pytest.mark.asyncio
async def test_widget_session_burst_shared_across_two_limiters() -> None:
    server = FakeServer()
    r1 = FakeRedis(server=server, decode_responses=True)
    r2 = FakeRedis(server=server, decode_responses=True)
    lim1 = RedisSlidingWindowLimiter(r1, key_prefix="itest:wg:")
    lim2 = RedisSlidingWindowLimiter(r2, key_prefix="itest:wg:")
    limit = 4
    for i in range(limit):
        o = await lim1.consume("pub_wg_sess_burst:digest:s:abc", limit=limit, window_seconds=60.0)
        assert o.allowed, i
    blocked = await lim2.consume("pub_wg_sess_burst:digest:s:abc", limit=limit, window_seconds=60.0)
    assert not blocked.allowed
    await r1.aclose()
    await r2.aclose()


@pytest.mark.asyncio
async def test_enforce_widget_abuse_identical_burst_uses_redis_when_tracker_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.core.public_widget_abuse.client_ip",
        lambda *_a, **_kw: "192.0.2.50",
    )
    server = FakeServer()
    r = FakeRedis(server=server, decode_responses=True)
    lim = RedisSlidingWindowLimiter(r, key_prefix="itest:ab:")
    tracker = RedisWidgetStreakTracker(r, key_prefix="itest:ab:wg:str:")
    settings = MagicMock()
    settings.rate_limiting_enabled = True
    settings.public_widget_abuse_enabled = True
    settings.public_widget_abuse_max_message_chars = 0
    settings.public_widget_abuse_session_burst_per_minute = 0
    settings.public_widget_abuse_identical_total_per_window = 2
    settings.public_widget_abuse_identical_window_seconds = 300.0
    settings.public_widget_abuse_max_consecutive_identical = 0
    settings.trust_forwarded_for = False
    settings.rate_limit_public_fail_open_on_redis_error = True

    req = MagicMock()
    pk = "widget_pk_integration"
    text = "same text"
    try:
        for _ in range(2):
            await enforce_public_widget_chat_turn(
                request=req,
                settings=settings,
                public_widget_key=pk,
                message_text=text,
                visitor_session_key="visitor-sess-integration-123456789012",
                limiter=lim,
                streak_tracker=tracker,
            )
        with pytest.raises(HTTPException) as ei:
            await enforce_public_widget_chat_turn(
                request=req,
                settings=settings,
                public_widget_key=pk,
                message_text=text,
                visitor_session_key="visitor-sess-integration-123456789012",
                limiter=lim,
                streak_tracker=tracker,
            )
        assert ei.value.status_code == 429
    finally:
        reset_public_widget_abuse_memory_for_tests()
        await r.aclose()
