"""
Google Gemini (Generative Language API) — production integration.

Environment (see also :class:`~app.core.config.Settings`):

* ``GEMINI_API_KEY`` / ``APP_GEMINI_API_KEY`` — required for live calls
* ``GEMINI_DEFAULT_MODEL`` / ``APP_GEMINI_DEFAULT_MODEL`` — model id when ``GenerateParams.model`` is empty
* ``GEMINI_API_BASE_URL`` / ``APP_GEMINI_API_BASE_URL`` — API root (default: official v1beta URL)
* ``GEMINI_REQUEST_TIMEOUT_SECONDS`` / ``APP_GEMINI_REQUEST_TIMEOUT_SECONDS`` — read/write timeout
* ``GEMINI_CONNECT_TIMEOUT_SECONDS`` / ``APP_GEMINI_CONNECT_TIMEOUT_SECONDS`` — connect timeout

The API key is sent as ``x-goog-api-key`` (not a query param) so URLs stay out of access logs with secrets.

Message roles: ``system`` → ``systemInstruction``; ``user`` / ``assistant`` → contents (assistant maps to
Gemini ``model``). Pass prior turns as a list of :class:`~app.ai_providers.types.ChatMessage` in
``GenerateParams.messages`` — no prompt templating here.
"""

from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Mapping

import httpx

from app.ai_providers.base import AIProvider
from app.ai_providers.types import ChatMessage, GenerateParams, NormalizedAIResult, TokenUsage
from app.core.config import Settings
from app.core.logging import get_logger

from . import gemini_errors
from .gemini_usage import parse_gemini_usage_metadata

_LOG = get_logger(__name__)

_DEFAULT_PUBLIC_BASE = "https://generativelanguage.googleapis.com/v1beta"
_FALLBACK_MODEL = "gemini-2.5-flash"
# Transient Gemini quota / RPM bursts often recover within a few seconds.
_GEMINI_429_MAX_ATTEMPTS = 4
_GEMINI_429_BACKOFF_CAP_S = 60.0


def _sleep_before_gemini_429_retry(response: httpx.Response, attempt_index: int) -> float:
    """
    Seconds to wait before the next generateContent attempt after HTTP 429.

    Honors ``Retry-After`` when it is a small positive integer; otherwise exponential
    backoff with light jitter (capped).
    """
    raw = (response.headers.get("Retry-After") or "").strip()
    if raw.isdigit():
        sec = float(int(raw))
        if 0 < sec <= _GEMINI_429_BACKOFF_CAP_S:
            return sec
    # HTTP-date form — best-effort; ignore on failure
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            if dt is not None:
                now = datetime.now(timezone.utc)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                delta = (dt - now).total_seconds()
                if 0 < delta <= _GEMINI_429_BACKOFF_CAP_S:
                    return float(delta)
        except (TypeError, ValueError, OSError):
            pass
    base = min(_GEMINI_429_BACKOFF_CAP_S, float(2**attempt_index))
    return min(_GEMINI_429_BACKOFF_CAP_S, base + random.random() * 0.5)


def _model_supports_gemini_thinking_config(model: str) -> bool:
    """Gemini 2.5+ hybrid models accept ``generationConfig.thinkingConfig`` (see Google thinking docs)."""
    m = (model or "").strip().lower()
    return m.startswith("gemini-2.5") or m.startswith("gemini-3")


# finishReason values that should surface as blocked / policy (not MAX_TOKENS; that may still return text)
_CONTENT_BLOCKED_FINISH = frozenset(
    {
        "SAFETY",
        "RECITATION",
        "BLOCKLIST",
        "PROHIBITED_CONTENT",
        "SPII",
        "OTHER",
    }
)


def _contents_from_messages(messages: tuple[ChatMessage, ...]) -> tuple[list[dict[str, Any]], str | None]:
    system_chunks: list[str] = []
    contents: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "system":
            system_chunks.append(m.content)
            continue
        gemini_role = "model" if m.role == "assistant" else "user"
        contents.append({"role": gemini_role, "parts": [{"text": m.content}]})
    system_instruction = "\n\n".join(system_chunks) if system_chunks else None
    return contents, system_instruction


def _extract_text_and_finish(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (concatenated text, finish_reason or None)."""
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None, None
    first = candidates[0]
    if not isinstance(first, dict):
        return None, None
    finish = first.get("finishReason")
    finish_s = str(finish).strip().upper() if finish is not None else None
    parts = first.get("content", {})
    if not isinstance(parts, dict):
        return None, finish_s
    part_list = parts.get("parts")
    if not isinstance(part_list, list) or not part_list:
        return None, finish_s
    texts: list[str] = []
    for p in part_list:
        if isinstance(p, dict) and "text" in p:
            texts.append(str(p.get("text", "")))
    text_out = "".join(texts) if texts else None
    return (text_out if text_out else None), finish_s


class GeminiProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        *,
        default_model: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        base_url: str = _DEFAULT_PUBLIC_BASE,
        request_timeout_seconds: float = 120.0,
        connect_timeout_seconds: float = 10.0,
        send_thinking_config: bool = True,
        thinking_budget: int = 0,
    ) -> None:
        self._api_key = api_key
        self._default_model = (default_model or _FALLBACK_MODEL).strip() or _FALLBACK_MODEL
        self._send_thinking_config = bool(send_thinking_config)
        self._thinking_budget = int(thinking_budget)
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
    def from_settings(cls, settings: Settings, *, http_client: httpx.AsyncClient | None = None) -> GeminiProvider:
        return cls(
            api_key=str(settings.gemini_api_key).strip(),
            default_model=settings.gemini_default_model,
            http_client=http_client,
            base_url=settings.gemini_api_base_url,
            request_timeout_seconds=settings.gemini_request_timeout_seconds,
            connect_timeout_seconds=settings.gemini_connect_timeout_seconds,
            send_thinking_config=settings.gemini_send_thinking_config,
            thinking_budget=int(settings.gemini_thinking_budget),
        )

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return self._default_model

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def parse_usage(self, raw: Mapping[str, Any] | None) -> TokenUsage | None:
        return parse_gemini_usage_metadata(raw if isinstance(raw, Mapping) else None)

    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        code, msg = gemini_errors.normalize_provider_exception(exc)
        return (code, msg)

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        contents, system_instruction = _contents_from_messages(params.messages)
        if not contents:
            return NormalizedAIResult(
                success=False,
                provider_name=self.provider_name,
                text=None,
                model_name=params.model.strip() or self._default_model,
                error_code=gemini_errors.INVALID_REQUEST,
                error_message="At least one user or assistant message is required.",
            )

        body: dict[str, Any] = {"contents": contents}
        if system_instruction is not None:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        model = params.model.strip() or self._default_model
        gen_cfg: dict[str, Any] = {}
        if params.temperature is not None:
            gen_cfg["temperature"] = params.temperature
        if params.max_output_tokens is not None:
            gen_cfg["maxOutputTokens"] = params.max_output_tokens
        if self._send_thinking_config and _model_supports_gemini_thinking_config(model):
            gen_cfg["thinkingConfig"] = {"thinkingBudget": self._thinking_budget}
        if gen_cfg:
            body["generationConfig"] = gen_cfg

        url = f"/models/{model}:generateContent"

        try:
            r: httpx.Response | None = None
            for attempt in range(_GEMINI_429_MAX_ATTEMPTS):
                # Header avoids putting the key in the request URL (access logs, error reports).
                r = await self._client.post(
                    url,
                    json=body,
                    headers={"x-goog-api-key": self._api_key},
                )
                if r.status_code == 429 and attempt < _GEMINI_429_MAX_ATTEMPTS - 1:
                    delay = _sleep_before_gemini_429_retry(r, attempt)
                    _LOG.warning(
                        "gemini_generate_content_429_retry",
                        model=model,
                        attempt=attempt + 1,
                        max_attempts=_GEMINI_429_MAX_ATTEMPTS,
                        sleep_seconds=round(delay, 3),
                    )
                    await asyncio.sleep(delay)
                    continue
                try:
                    r.raise_for_status()
                except httpx.HTTPStatusError as e:
                    return self._failure_from_http_error(e, model)
                break
            assert r is not None
        except httpx.TimeoutException as e:
            code, msg = self.normalize_error(e)
            _LOG.warning(
                "gemini_generate_content_timeout",
                model=model,
                exc_type=type(e).__name__,
                normalized_error_code=code,
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
                "gemini_generate_content_request_error",
                model=model,
                exc_type=type(e).__name__,
                normalized_error_code=code,
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
            _LOG.warning(
                "gemini_generate_content_json_error",
                model=model,
                exc_type=type(e).__name__,
                normalized_error_code=code,
            )
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
                error_code=gemini_errors.INVALID_RESPONSE,
                error_message="AI provider returned a non-object JSON body.",
            )

        raw_usage = payload.get("usageMetadata")
        usage_dict = raw_usage if isinstance(raw_usage, dict) else None
        tokens = self.parse_usage(usage_dict)

        text_out, finish_reason = _extract_text_and_finish(payload)

        if finish_reason and finish_reason in _CONTENT_BLOCKED_FINISH:
            return NormalizedAIResult(
                success=False,
                provider_name=self.provider_name,
                text=None,
                model_name=model,
                tokens=tokens,
                raw_usage=dict(usage_dict) if usage_dict is not None else None,
                error_code="content_blocked",
                error_message="The model stopped for safety or policy reasons.",
            )

        if text_out is not None:
            return NormalizedAIResult(
                success=True,
                provider_name=self.provider_name,
                text=text_out,
                model_name=model,
                tokens=tokens,
                raw_usage=dict(usage_dict) if usage_dict is not None else None,
            )

        if finish_reason == "MAX_TOKENS":
            return NormalizedAIResult(
                success=False,
                provider_name=self.provider_name,
                text=None,
                model_name=model,
                tokens=tokens,
                raw_usage=dict(usage_dict) if usage_dict is not None else None,
                error_code="max_tokens",
                error_message="The model hit the output token limit with no visible text.",
            )

        return NormalizedAIResult(
            success=False,
            provider_name=self.provider_name,
            text=None,
            model_name=model,
            tokens=tokens,
            raw_usage=dict(usage_dict) if usage_dict is not None else None,
            error_code=gemini_errors.INVALID_RESPONSE,
            error_message="AI provider returned no text content.",
        )

    def _failure_from_http_error(self, e: httpx.HTTPStatusError, model: str) -> NormalizedAIResult:
        code, msg = self.normalize_error(e)
        body_snippet = ""
        try:
            body_snippet = (e.response.text or "").strip()[:800]
        except Exception:
            pass
        _LOG.warning(
            "gemini_generate_content_http_error",
            model=model,
            http_status=e.response.status_code,
            normalized_error_code=code,
            response_body_snippet=body_snippet,
        )
        raw_usage_dict: dict[str, Any] | None = None
        try:
            parsed = e.response.json()
            if isinstance(parsed, dict):
                ru = parsed.get("usageMetadata")
                if isinstance(ru, dict):
                    raw_usage_dict = ru
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        return NormalizedAIResult(
            success=False,
            provider_name=self.provider_name,
            text=None,
            model_name=model,
            tokens=self.parse_usage(raw_usage_dict),
            raw_usage=dict(raw_usage_dict) if raw_usage_dict is not None else None,
            error_code=code,
            error_message=msg,
        )


__all__ = ["GeminiProvider"]
