"""Unit tests for AI provider abstraction (no live API calls)."""

from __future__ import annotations

import asyncio
import dataclasses

import httpx
import pytest
from app.ai_providers.base import AIProvider
from app.ai_providers.exceptions import MissingAIProviderCredentialsError, UnknownAIProviderError
from app.ai_providers.gemini import GeminiProvider
from app.ai_providers.registry import (
    default_provider_id,
    registered_provider_ids,
    resolve_ai_provider,
)
from app.ai_providers.types import ChatMessage, GenerateParams, NormalizedAIResult, TokenUsage
from app.core.config import Settings
from app.integrations.providers import gemini_errors
from app.integrations.providers.gemini_usage import parse_gemini_usage_metadata, usage_estimation_recommended

# Contract guard: bump intentionally if the normalized shape changes for API/DB consumers.
_EXPECTED_NORMALIZED_AI_RESULT_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "success",
        "provider_name",
        "text",
        "model_name",
        "tokens",
        "raw_usage",
        "error_code",
        "error_message",
    }
)


def test_ai_provider_interface_is_abstract() -> None:
    with pytest.raises(TypeError, match="abstract"):
        AIProvider()  # type: ignore[misc]


def test_normalized_ai_result_field_contract_is_stable() -> None:
    actual = frozenset(f.name for f in dataclasses.fields(NormalizedAIResult))
    assert actual == _EXPECTED_NORMALIZED_AI_RESULT_FIELD_NAMES
    assert dataclasses.is_dataclass(NormalizedAIResult)
    assert getattr(NormalizedAIResult, "__slots__", None) is not None


def test_normalized_ai_result_success_and_failure_shapes() -> None:
    ok = NormalizedAIResult(
        success=True,
        provider_name="gemini",
        text="hi",
        model_name="gemini-2.5-flash",
        tokens=TokenUsage(input_tokens=1, output_tokens=2, total_tokens=3),
        raw_usage={"totalTokenCount": 3},
        error_code=None,
        error_message=None,
    )
    assert ok.success is True and ok.text == "hi" and ok.error_code is None

    bad = NormalizedAIResult(
        success=False,
        provider_name="gemini",
        text=None,
        model_name="gemini-2.5-flash",
        tokens=None,
        raw_usage=None,
        error_code="INVALID_ARGUMENT",
        error_message="bad",
    )
    assert bad.success is False and bad.text is None and bad.error_message == "bad"


def test_generate_params_and_chat_message_are_frozen() -> None:
    p = GenerateParams(model="m", messages=(ChatMessage(role="user", content="x"),))
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.model = "y"  # type: ignore[misc]


def test_registered_providers_include_gemini() -> None:
    assert "gemini" in registered_provider_ids()
    assert default_provider_id() == "gemini"


def _settings_with_gemini_key(key: str = "secret-key") -> Settings:
    return Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": key,
        }
    )


@pytest.mark.parametrize("provider_arg", [None, "", "   ", "gemini", "GEMINI", " GeMini "])
def test_resolve_ai_provider_returns_gemini_implementation(provider_arg: str | None) -> None:
    s = _settings_with_gemini_key()
    p = resolve_ai_provider(s, provider_arg)
    assert isinstance(p, GeminiProvider)
    assert isinstance(p, AIProvider)
    assert p.provider_name == "gemini"


def test_resolve_unknown_provider_fails_cleanly() -> None:
    s = _settings_with_gemini_key()
    with pytest.raises(UnknownAIProviderError) as excinfo:
        resolve_ai_provider(s, "openai")
    assert excinfo.value.provider_id == "openai"


def test_resolve_gemini_requires_api_key() -> None:
    s = Settings.model_validate({"database_url": "postgresql+asyncpg://u:p@localhost:5432/db"})
    with pytest.raises(MissingAIProviderCredentialsError) as excinfo:
        resolve_ai_provider(s, "gemini")
    assert excinfo.value.provider_id == "gemini"
    assert "GEMINI_API_KEY" in str(excinfo.value)


def test_resolve_gemini_rejects_whitespace_only_api_key() -> None:
    s = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "   \t  ",
        }
    )
    with pytest.raises(MissingAIProviderCredentialsError) as excinfo:
        resolve_ai_provider(s, None)
    assert excinfo.value.provider_id == "gemini"


def test_gemini_parse_usage() -> None:
    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))) as c:
            p = GeminiProvider(api_key="k", http_client=c)
            assert p.parse_usage(None) is None
            u = p.parse_usage({"promptTokenCount": 1, "candidatesTokenCount": 2, "totalTokenCount": 3})
            assert u == TokenUsage(input_tokens=1, output_tokens=2, total_tokens=3)

    asyncio.run(run())


def test_gemini_normalize_error() -> None:
    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))) as c:
            p = GeminiProvider(api_key="k", http_client=c)
            req = httpx.Request("GET", "https://example.com")
            resp = httpx.Response(
                429,
                request=req,
                json={"error": {"status": "RESOURCE_EXHAUSTED", "message": "Quota exceeded"}},
            )
            exc = httpx.HTTPStatusError("msg", request=req, response=resp)
            code, msg = p.normalize_error(exc)
            assert code == "rate_limited"
            assert "Quota" in msg

    asyncio.run(run())


def test_parse_gemini_usage_accepts_snake_case() -> None:
    u = parse_gemini_usage_metadata(
        {"prompt_token_count": 2, "candidates_token_count": 3, "total_token_count": 5}
    )
    assert u is not None
    assert u.input_tokens == 2 and u.output_tokens == 3 and u.total_tokens == 5


def test_usage_estimation_recommended_hook() -> None:
    need = NormalizedAIResult(
        success=True,
        provider_name="gemini",
        text="hello",
        model_name="m",
        tokens=None,
    )
    assert usage_estimation_recommended(need) is True
    skip = NormalizedAIResult(
        success=True,
        provider_name="gemini",
        text="hello",
        model_name="m",
        tokens=TokenUsage(input_tokens=1, output_tokens=1, total_tokens=2),
    )
    assert usage_estimation_recommended(skip) is False


def test_normalize_error_maps_auth_and_timeout() -> None:
    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))) as c:
            p = GeminiProvider(api_key="k", http_client=c)
            req = httpx.Request("GET", "https://example.com")
            resp_401 = httpx.Response(401, request=req, text="nope")
            e401 = httpx.HTTPStatusError("m", request=req, response=resp_401)
            c401, _ = p.normalize_error(e401)
            assert c401 == gemini_errors.AUTH_FAILED

            te = httpx.ReadTimeout("t", request=req)
            ct, _ = p.normalize_error(te)
            assert ct == gemini_errors.TIMEOUT

    asyncio.run(run())


def test_gemini_uses_default_model_when_param_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "gemini-9.9-test" in request.url.path
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "OK"}]}}]},
        )

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://generativelanguage.googleapis.com/v1beta"
        ) as client:
            p = GeminiProvider(api_key="secret", http_client=client, default_model="gemini-9.9-test")
            out = await p.generate_response(
                GenerateParams(model="   ", messages=(ChatMessage(role="user", content="Hi"),)),
            )
            assert out.success and out.text == "OK"
            assert out.model_name == "gemini-9.9-test"

    asyncio.run(run())


def test_gemini_generate_response_invalid_json_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

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
            assert out.success is False
            assert out.error_code == gemini_errors.INVALID_RESPONSE

    asyncio.run(run())


def test_gemini_generate_response_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith(":generateContent")
        assert request.headers.get("x-goog-api-key") == "secret"
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "Hello"}]}}],
                "usageMetadata": {
                    "promptTokenCount": 5,
                    "candidatesTokenCount": 1,
                    "totalTokenCount": 6,
                },
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
                    messages=(ChatMessage(role="user", content="Hi"),),
                )
            )
            assert out.success is True
            assert out.text == "Hello"
            assert out.model_name == "gemini-2.5-flash"
            assert out.tokens is not None
            assert out.tokens.input_tokens == 5
            assert out.raw_usage is not None
            assert out.raw_usage["totalTokenCount"] == 6

    asyncio.run(run())


def test_gemini_generate_response_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"status": "INVALID_ARGUMENT", "message": "bad"}})

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
            assert out.success is False
            assert out.text is None
            assert out.error_code == "INVALID_ARGUMENT"

    asyncio.run(run())
