"""
Ollama (local LLM) — cost-free alternative to cloud providers.

Environment (see also :class:`~app.core.config.Settings`):

* ``OLLAMA_BASE_URL`` / ``APP_OLLAMA_BASE_URL`` — Ollama API root (default: http://ollama:11434)
* ``OLLAMA_DEFAULT_MODEL`` / ``APP_OLLAMA_DEFAULT_MODEL`` — model id (default: qwen2.5:7b)
* ``OLLAMA_REQUEST_TIMEOUT_SECONDS`` / ``APP_OLLAMA_REQUEST_TIMEOUT_SECONDS`` — read timeout
* ``OLLAMA_CONNECT_TIMEOUT_SECONDS`` / ``APP_OLLAMA_CONNECT_TIMEOUT_SECONDS`` — connect timeout

Ollama runs locally (Docker sidecar or host machine), so there is **no API key** and
**zero cost per token**. The ``/api/chat`` endpoint uses an OpenAI-compatible message
format (system / user / assistant roles) with streaming disabled for simplicity.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

import httpx

from app.ai_providers.base import AIProvider
from app.ai_providers.types import ChatMessage, GenerateParams, NormalizedAIResult, TokenUsage
from app.core.config import Settings
from app.core.logging import get_logger

_LOG = get_logger(__name__)

_DEFAULT_BASE_URL = "http://ollama:11434"
_FALLBACK_MODEL = "qwen2.5:7b"

# Error codes (consistent with gemini_errors style)
INVALID_REQUEST = "invalid_request"
INVALID_RESPONSE = "invalid_response"
MODEL_NOT_FOUND = "model_not_found"
CONNECTION_ERROR = "connection_error"
TIMEOUT_ERROR = "timeout"


def _messages_from_chat(messages: tuple[ChatMessage, ...]) -> list[dict[str, str]]:
    """Convert internal ChatMessage tuples to Ollama /api/chat format.

    Ollama natively supports ``system``, ``user``, and ``assistant`` roles —
    no remapping needed (unlike Gemini which uses ``model`` instead of ``assistant``).
    """
    return [{"role": m.role, "content": m.content} for m in messages]


class OllamaProvider(AIProvider):
    """Local Ollama inference via ``/api/chat`` (non-streaming)."""

    def __init__(
        self,
        *,
        default_model: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        request_timeout_seconds: float = 120.0,
        connect_timeout_seconds: float = 10.0,
    ) -> None:
        self._default_model = (default_model or _FALLBACK_MODEL).strip() or _FALLBACK_MODEL
        self._owns_client = http_client is None
        timeout = httpx.Timeout(
            timeout=request_timeout_seconds,
            connect=connect_timeout_seconds,
        )
        self._client = http_client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
        )

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> OllamaProvider:
        return cls(
            default_model=settings.ollama_default_model,
            http_client=http_client,
            base_url=settings.ollama_base_url,
            request_timeout_seconds=settings.ollama_request_timeout_seconds,
            connect_timeout_seconds=settings.ollama_connect_timeout_seconds,
        )

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def default_model(self) -> str:
        return self._default_model

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def parse_usage(self, raw: Mapping[str, Any] | None) -> TokenUsage | None:
        if raw is None:
            return None
        prompt = raw.get("prompt_eval_count")
        completion = raw.get("eval_count")
        inp = int(prompt) if isinstance(prompt, (int, float)) and prompt >= 0 else None
        out = int(completion) if isinstance(completion, (int, float)) and completion >= 0 else None
        total = (inp or 0) + (out or 0) if inp is not None or out is not None else None
        if inp is None and out is None:
            return None
        return TokenUsage(input_tokens=inp, output_tokens=out, total_tokens=total)

    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            body = ""
            try:
                body = (exc.response.text or "").strip()[:500]
            except Exception:
                pass
            if status == 404:
                return MODEL_NOT_FOUND, f"Ollama model not found: {body}"
            return f"http_{status}", f"Ollama API error ({status}): {body}"
        if isinstance(exc, httpx.TimeoutException):
            return TIMEOUT_ERROR, f"Ollama request timed out: {type(exc).__name__}"
        if isinstance(exc, httpx.ConnectError):
            return CONNECTION_ERROR, (
                "Cannot connect to Ollama. Is it running? "
                "Check OLLAMA_BASE_URL and ensure the service is accessible."
            )
        if isinstance(exc, httpx.RequestError):
            return CONNECTION_ERROR, f"Ollama connection error: {type(exc).__name__}: {exc!s}"
        if isinstance(exc, json.JSONDecodeError):
            return INVALID_RESPONSE, "Ollama returned invalid JSON."
        return None, f"Unexpected Ollama error: {type(exc).__name__}: {exc!s}"

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        ollama_messages = _messages_from_chat(params.messages)
        if not ollama_messages:
            return NormalizedAIResult(
                success=False,
                provider_name=self.provider_name,
                text=None,
                model_name=params.model.strip() or self._default_model,
                error_code=INVALID_REQUEST,
                error_message="At least one message is required.",
            )

        model = params.model.strip() or self._default_model
        body: dict[str, Any] = {
            "model": model,
            "messages": ollama_messages,
            "stream": False,
        }

        options: dict[str, Any] = {}
        if params.temperature is not None:
            options["temperature"] = params.temperature
        if params.max_output_tokens is not None:
            options["num_predict"] = params.max_output_tokens
        if options:
            body["options"] = options

        try:
            r = await self._client.post("/api/chat", json=body)
            try:
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                return self._failure_from_http_error(e, model)
        except httpx.TimeoutException as e:
            code, msg = self.normalize_error(e)
            _LOG.warning(
                "ollama_chat_timeout",
                model=model,
                exc_type=type(e).__name__,
                error_detail=str(e)[:500],
            )
            return NormalizedAIResult(
                success=False,
                provider_name=self.provider_name,
                text=None,
                model_name=model,
                error_code=code,
                error_message=msg,
            )
        except httpx.RequestError as e:
            code, msg = self.normalize_error(e)
            _LOG.warning(
                "ollama_chat_connection_error",
                model=model,
                exc_type=type(e).__name__,
                error_detail=str(e)[:500],
            )
            return NormalizedAIResult(
                success=False,
                provider_name=self.provider_name,
                text=None,
                model_name=model,
                error_code=code,
                error_message=msg,
            )

        try:
            payload = r.json()
        except json.JSONDecodeError as e:
            code, msg = self.normalize_error(e)
            _LOG.warning("ollama_chat_json_error", model=model)
            return NormalizedAIResult(
                success=False,
                provider_name=self.provider_name,
                text=None,
                model_name=model,
                error_code=code,
                error_message=msg,
            )

        if not isinstance(payload, dict):
            return NormalizedAIResult(
                success=False,
                provider_name=self.provider_name,
                text=None,
                model_name=model,
                error_code=INVALID_RESPONSE,
                error_message="Ollama returned a non-object JSON body.",
            )

        # Extract usage from Ollama response fields
        usage_dict: dict[str, Any] = {
            "prompt_eval_count": payload.get("prompt_eval_count"),
            "eval_count": payload.get("eval_count"),
        }
        tokens = self.parse_usage(usage_dict)

        # Extract text from message.content
        message = payload.get("message")
        text_out: str | None = None
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                text_out = content.strip()

        if text_out is not None:
            return NormalizedAIResult(
                success=True,
                provider_name=self.provider_name,
                text=text_out,
                model_name=model,
                tokens=tokens,
                raw_usage=usage_dict if tokens else None,
            )

        # Check for error field in response
        error_msg = payload.get("error")
        if isinstance(error_msg, str) and error_msg.strip():
            return NormalizedAIResult(
                success=False,
                provider_name=self.provider_name,
                text=None,
                model_name=model,
                tokens=tokens,
                raw_usage=usage_dict if tokens else None,
                error_code=INVALID_RESPONSE,
                error_message=f"Ollama error: {error_msg.strip()[:500]}",
            )

        return NormalizedAIResult(
            success=False,
            provider_name=self.provider_name,
            text=None,
            model_name=model,
            tokens=tokens,
            raw_usage=usage_dict if tokens else None,
            error_code=INVALID_RESPONSE,
            error_message="Ollama returned no text content.",
        )

    def _failure_from_http_error(
        self, e: httpx.HTTPStatusError, model: str,
    ) -> NormalizedAIResult:
        code, msg = self.normalize_error(e)
        _LOG.warning(
            "ollama_chat_http_error",
            model=model,
            http_status=e.response.status_code,
            normalized_error_code=code,
            response_body_snippet=(e.response.text or "").strip()[:500],
        )
        return NormalizedAIResult(
            success=False,
            provider_name=self.provider_name,
            text=None,
            model_name=model,
            error_code=code,
            error_message=msg,
        )


__all__ = ["OllamaProvider"]
