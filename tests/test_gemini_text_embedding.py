"""Unit tests for Gemini embedContent client."""

from __future__ import annotations

import json

import httpx
import pytest

from app.integrations.gemini_text_embedding import (
    GeminiEmbeddingError,
    _embedding_v1_root_from_chat_base,
    gemini_embed_text,
)


def test_embedding_v1_root_maps_v1beta() -> None:
    assert _embedding_v1_root_from_chat_base(
        "https://generativelanguage.googleapis.com/v1beta"
    ) == "https://generativelanguage.googleapis.com/v1"
    assert _embedding_v1_root_from_chat_base(
        "https://generativelanguage.googleapis.com/v1"
    ) == "https://generativelanguage.googleapis.com/v1"


@pytest.mark.asyncio
async def test_gemini_embed_posts_model_resource_in_json_body_and_uses_v1() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"embedding": {"values": [0.25, 0.5]}},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        out = await gemini_embed_text(
            api_key="dummy",
            base_url="https://generativelanguage.googleapis.com/v1beta",
            model="models/text-embedding-004",
            text="hi",
            client=client,
        )
    assert out == [0.25, 0.5]
    assert captured["url"].endswith("/v1/models/text-embedding-004:embedContent")
    body = captured["body"]
    assert isinstance(body, dict)
    assert body.get("model") == "models/text-embedding-004"
    assert body.get("content", {}).get("parts")


@pytest.mark.asyncio
async def test_gemini_embed_strips_duplicate_models_prefix_in_url() -> None:
    urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        urls.append(str(request.url))
        return httpx.Response(200, json={"embedding": {"values": [1.0]}})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        await gemini_embed_text(
            api_key="dummy",
            base_url="https://generativelanguage.googleapis.com/v1beta",
            model="models/models/text-embedding-004",
            text="x",
            client=client,
        )
    assert urls[0].endswith("/v1/models/text-embedding-004:embedContent")


@pytest.mark.asyncio
async def test_gemini_embed_fail_open_returns_none_on_404() -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(404, text='{"error":"no"}'))
    async with httpx.AsyncClient(transport=transport) as client:
        out = await gemini_embed_text(
            api_key="dummy",
            base_url="https://generativelanguage.googleapis.com/v1beta",
            model="models/text-embedding-004",
            text="x",
            client=client,
            fail_open=True,
        )
    assert out is None


@pytest.mark.asyncio
async def test_gemini_embed_fail_open_false_raises() -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(404, text="not found"))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(GeminiEmbeddingError) as ei:
            await gemini_embed_text(
                api_key="dummy",
                base_url="https://generativelanguage.googleapis.com/v1beta",
                model="models/text-embedding-004",
                text="x",
                client=client,
                fail_open=False,
            )
    assert ei.value.status_code == 404
