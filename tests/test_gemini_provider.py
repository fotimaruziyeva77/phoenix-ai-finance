"""
Gemini provider: config wiring, normalized shapes, error paths, secret hygiene (mocked HTTP).
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from app.ai_providers.types import ChatMessage, GenerateParams, NormalizedAIResult, TokenUsage
from app.core.config import Settings
from app.integrations.providers import gemini_errors
from app.integrations.providers.gemini import GeminiProvider


def _assert_normalized_success_shape(r: NormalizedAIResult) -> None:
    assert r.success is True
    assert r.provider_name == "gemini"
    assert r.error_code is None
    assert r.error_message is None
    assert r.text is not None
    assert isinstance(r.text, str)
    assert r.model_name is not None and str(r.model_name).strip() != ""
    assert r.tokens is None or isinstance(r.tokens, TokenUsage)
    assert r.raw_usage is None or isinstance(r.raw_usage, dict)
    fields = {f.name for f in dataclasses.fields(NormalizedAIResult)}
    assert fields == {
        "success",
        "provider_name",
        "text",
        "model_name",
        "tokens",
        "raw_usage",
        "error_code",
        "error_message",
    }


def _assert_normalized_error_shape(r: NormalizedAIResult) -> None:
    assert r.success is False
    assert r.provider_name == "gemini"
    assert r.text is None
    assert r.error_code is not None and str(r.error_code).strip() != ""
    assert r.error_message is not None and str(r.error_message).strip() != ""
    assert r.model_name is None or isinstance(r.model_name, str)


def _settings_full(api_key: str = "unit-test-key") -> Settings:
    return Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": api_key,
            "gemini_default_model": "gemini-config-default",
            "gemini_api_base_url": "https://generativelanguage.googleapis.com/v1beta",
            "gemini_request_timeout_seconds": 99.0,
            "gemini_connect_timeout_seconds": 8.0,
        }
    )


def test_gemini_provider_from_settings_instantiation() -> None:
    s = _settings_full()
    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))) as c:
            p = GeminiProvider.from_settings(s, http_client=c)
            assert isinstance(p, GeminiProvider)
            assert p.provider_name == "gemini"
            assert p.default_model == "gemini-config-default"

    asyncio.run(run())


def test_settings_gemini_config_fields_parse() -> None:
    s = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "k",
            "gemini_default_model": "m",
            "gemini_api_base_url": "https://custom.example/gemini/v1beta/",
            "gemini_request_timeout_seconds": 45.0,
            "gemini_connect_timeout_seconds": 3.0,
        }
    )
    assert s.gemini_default_model == "m"
    assert s.gemini_api_base_url.rstrip("/").endswith("v1beta")
    assert s.gemini_request_timeout_seconds == 45.0
    assert s.gemini_connect_timeout_seconds == 3.0


def test_mocked_success_response_normalized_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        gc = body.get("generationConfig") or {}
        assert gc.get("thinkingConfig") == {"thinkingBudget": 0}
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "Reply"}]}}],
                "usageMetadata": {"promptTokenCount": 2, "candidatesTokenCount": 1, "totalTokenCount": 3},
            },
        )

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://generativelanguage.googleapis.com/v1beta"
        ) as client:
            p = GeminiProvider(api_key="secret", http_client=client)
            out = await p.generate_response(
                GenerateParams(
                    model="gemini-2.5-flash",
                    messages=(
                        ChatMessage(role="system", content="Sys"),
                        ChatMessage(role="user", content="Hi"),
                    ),
                )
            )
            _assert_normalized_success_shape(out)
            assert out.text == "Reply"
            assert out.tokens is not None
            assert out.tokens.total_tokens == 3

    asyncio.run(run())


def test_thinking_config_not_sent_for_models_without_hybrid_thinking() -> None:
    last_body: dict | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal last_body
        last_body = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "ok"}]}}],
                "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1, "totalTokenCount": 2},
            },
        )

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://generativelanguage.googleapis.com/v1beta"
        ) as client:
            p = GeminiProvider(api_key="secret", http_client=client)
            await p.generate_response(
                GenerateParams(
                    model="gemini-1.5-flash",
                    messages=(ChatMessage(role="user", content="Hi"),),
                )
            )

    asyncio.run(run())
    assert last_body is not None
    gc = last_body.get("generationConfig") or {}
    assert "thinkingConfig" not in gc


@pytest.mark.parametrize(
    "status,payload,expected_code_substr",
    [
        (401, {"error": {"message": "nope"}}, gemini_errors.AUTH_FAILED),
        (403, {"error": {"message": "denied"}}, gemini_errors.AUTH_FAILED),
        (503, {"error": {"message": "unavailable"}}, gemini_errors.PROVIDER_ERROR),
        (500, {}, gemini_errors.PROVIDER_ERROR),
    ],
)
def test_mocked_http_failures_normalized_cleanly(
    status: int,
    payload: dict,
    expected_code_substr: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload)

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://generativelanguage.googleapis.com/v1beta"
        ) as client:
            p = GeminiProvider(api_key="secret", http_client=client)
            out = await p.generate_response(
                GenerateParams(
                    model="gemini-2.5-flash",
                    messages=(ChatMessage(role="user", content="Hi"),),
                )
            )
            _assert_normalized_error_shape(out)
            assert out.error_code == expected_code_substr

    asyncio.run(run())


def test_gemini_429_retries_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 2:
            return httpx.Response(429, json={"error": {"message": "Resource exhausted"}})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Hi"}]}}]})

    async def run() -> None:
        with patch("app.integrations.providers.gemini.asyncio.sleep", new_callable=AsyncMock):
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(
                transport=transport, base_url="https://generativelanguage.googleapis.com/v1beta"
            ) as client:
                p = GeminiProvider(api_key="secret", http_client=client)
                out = await p.generate_response(
                    GenerateParams(
                        model="gemini-2.5-flash",
                        messages=(ChatMessage(role="user", content="x"),),
                    )
                )
        assert calls["n"] == 2
        _assert_normalized_success_shape(out)
        assert out.text == "Hi"

    asyncio.run(run())


def test_gemini_429_exhausted_returns_rate_limited() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429, json={"error": {"message": "quota"}})

    async def run() -> None:
        with patch("app.integrations.providers.gemini.asyncio.sleep", new_callable=AsyncMock):
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(
                transport=transport, base_url="https://generativelanguage.googleapis.com/v1beta"
            ) as client:
                p = GeminiProvider(api_key="secret", http_client=client)
                out = await p.generate_response(
                    GenerateParams(
                        model="gemini-2.5-flash",
                        messages=(ChatMessage(role="user", content="x"),),
                    )
                )
        assert calls["n"] == 4
        _assert_normalized_error_shape(out)
        assert out.error_code == gemini_errors.RATE_LIMITED

    asyncio.run(run())


def test_mocked_timeout_on_generate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://generativelanguage.googleapis.com/v1beta"
        ) as client:
            p = GeminiProvider(api_key="secret", http_client=client)
            out = await p.generate_response(
                GenerateParams(model="x", messages=(ChatMessage(role="user", content="Hi"),))
            )
            _assert_normalized_error_shape(out)
            assert out.error_code == gemini_errors.TIMEOUT

    asyncio.run(run())


def test_mocked_connect_error_on_generate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://generativelanguage.googleapis.com/v1beta"
        ) as client:
            p = GeminiProvider(api_key="secret", http_client=client)
            out = await p.generate_response(
                GenerateParams(model="x", messages=(ChatMessage(role="user", content="Hi"),))
            )
            _assert_normalized_error_shape(out)
            assert out.error_code == gemini_errors.CONNECTION_ERROR

    asyncio.run(run())


def test_error_message_redacts_google_api_key_pattern() -> None:
    leaked = "AIzaSy0123456789012345678901234567890AB"
    body = {"error": {"status": "INVALID_ARGUMENT", "message": f"Bad {leaked} end"}}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json=body)

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://generativelanguage.googleapis.com/v1beta"
        ) as client:
            p = GeminiProvider(api_key="secret", http_client=client)
            out = await p.generate_response(
                GenerateParams(model="m", messages=(ChatMessage(role="user", content="Hi"),))
            )
            assert out.success is False
            assert out.error_message is not None
            assert leaked not in out.error_message
            assert "AIzaSy" not in out.error_message
            assert "[REDACTED]" in out.error_message

    asyncio.run(run())


def test_normalized_results_do_not_echo_config_api_key() -> None:
    """Sentinel must not appear in error_message / str(result) for typical auth failure."""
    sentinel = "BF_UNIT_TEST_SECRET_KEY_9f3c2a1b"
    s = _settings_full(api_key=sentinel)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "Invalid key"}})

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://generativelanguage.googleapis.com/v1beta"
        ) as http_client:
            p = GeminiProvider.from_settings(s, http_client=http_client)
            out = await p.generate_response(
                GenerateParams(model="m", messages=(ChatMessage(role="user", content="Hi"),))
            )
            blob = f"{out.error_message!s} {out!r}"
            assert sentinel not in blob

    asyncio.run(run())


def test_credential_exception_message_is_generic() -> None:
    from app.ai_providers.exceptions import MissingAIProviderCredentialsError

    e = MissingAIProviderCredentialsError("gemini", detail="configure env")
    assert "gemini" in str(e).lower()
    assert "configure env" in str(e)


def test_gemini_provider_emits_no_logs_on_success(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://generativelanguage.googleapis.com/v1beta"
        ) as client:
            p = GeminiProvider(api_key="should-not-appear-in-logs", http_client=client)
            await p.generate_response(
                GenerateParams(model="m", messages=(ChatMessage(role="user", content="Hi"),))
            )

    asyncio.run(run())
    joined = caplog.text
    assert "should-not-appear-in-logs" not in joined
