"""
User intent classification (MVP): **hybrid rule-based + optional Gemini**.

* **Rules** handle obvious, high-precision cases with **no extra API cost** and **deterministic tests**.
* **Gemini** (tiny JSON-only prompt, low temperature) handles ambiguous phrasing when enabled.
* **Sales funnel default** (``sales_default``): when rules miss and the orchestrator disables the
  model, we use ``sales_interest`` so the state machine keeps a known intent (avoids ``unknown`` →
  ``fallback`` thrash) **without** an extra API call.
* **Unknown** when JSON is invalid, provider missing, or **confidence is below** ``_AI_CONFIDENCE_FLOOR``.

Sales bots: :class:`~app.services.sales_conversation_orchestrator.SalesConversationOrchestrator` calls
this before the state machine. Non-sales chat may use :class:`~app.services.ai_service.AIService` without
intent classification.

Niche-aware behavior: pass ``niche_hint`` (from :mod:`app.lib.niche_registry`); the model prompt
already includes a one-line niche line when provided.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Protocol

from app.ai_cost import build_pricing_catalog, calculate_cost, normalize_usage
from app.ai_providers.types import ChatMessage, GenerateParams, NormalizedAIResult
from app.core.ai_generation_policy import clamp_small_completion_budget
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.integrations.providers.gemini import GeminiProvider
from app.models.conversation_flow import ConversationDetectedIntent
from app.schemas.ai_usage import AI_USAGE_STEP_INTENT_CLASSIFIER, AIUsageLogPayload
from app.services.ai_usage_log_service import AIUsageLogService
from app.services.intent_ambiguity import sales_intent_message_ambiguous_for_gemini
from app.services.intent_rule_engine import classify_by_rules
from app.services.intent_types import (
    IntentClassificationResult,
    IntentClassifierUsageContext,
    coerce_intent_label,
)

_LOG = logging.getLogger(__name__)
_SLOG = get_logger(__name__)

_AI_CONFIDENCE_FLOOR = 0.42

_SYSTEM_PROMPT = """You are an intent classifier for a business chatbot. Output ONLY valid JSON, no markdown.

Schema: {"intent":"<label>","confidence":<number between 0 and 1>}

Allowed intent labels (exactly):
greeting, sales_interest, support, faq, consulting, unknown

Definitions:
- greeting: short hello/hi without a business request.
- sales_interest: buying, pricing, demo, quote, signup interest.
- support: something broken, errors, refunds, tickets, troubleshooting.
- faq: general informational questions about the product or company.
- consulting: strategy, audits, professional services, workshops.
- unknown: unclear, off-topic, or mixed intents you cannot assign confidently.

If unsure, use unknown with confidence under 0.5."""


def _niche_line(niche_hint: str | None) -> str:
    h = (niche_hint or "").strip()
    if not h:
        return ""
    return f"\nNiche context (weak hint only): {h[:200]}"


def _extract_json_object(text: str | None) -> dict[str, object] | None:
    if not text or not str(text).strip():
        return None
    t = str(text).strip()
    if t.startswith("```"):
        t = re.sub(r"^```\w*\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```\s*$", "", t)
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    start, end = t.find("{"), t.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(t[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _confidence_from_payload(obj: dict[str, object]) -> float:
    raw = obj.get("confidence")
    if isinstance(raw, bool):
        return 1.0 if raw else 0.0
    if isinstance(raw, (int, float)):
        return max(0.0, min(1.0, float(raw)))
    return 0.55


def _cache_key(
    text: str,
    niche_hint: str | None,
    *,
    use_ai_when_rules_miss: bool,
    sales_funnel_bot: bool,
) -> str:
    n = (niche_hint or "").strip()[:200]
    return f"{int(use_ai_when_rules_miss)}|{int(sales_funnel_bot)}|{n}|{text[:500]}"


class SupportsIntentAI(Protocol):
    """Minimal surface for tests (mock ``AIProvider``)."""

    async def generate_response(self, params: GenerateParams): ...


class IntentClassifierService:
    """
    Classify a single user message into :class:`~app.models.conversation_flow.ConversationDetectedIntent`.

    Inject ``ai_provider`` for unit tests; otherwise a :class:`~app.integrations.providers.gemini.GeminiProvider`
    is built from settings when AI classification is needed.
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        ai_provider: SupportsIntentAI | None = None,
        usage_log_service: AIUsageLogService | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._ai_provider = ai_provider
        self._usage_logs = usage_log_service
        self._cache: dict[str, tuple[float, IntentClassificationResult]] = {}
        self._cache_lock = asyncio.Lock()

    def _resolve_provider(self) -> SupportsIntentAI | None:
        if self._ai_provider is not None:
            return self._ai_provider
        key = (self._settings.gemini_api_key or "").strip()
        if not key:
            return None
        return GeminiProvider.from_settings(self._settings)

    async def _cache_get(self, key: str) -> IntentClassificationResult | None:
        ttl = int(self._settings.ai_intent_classifier_cache_ttl_seconds)
        if ttl <= 0:
            return None
        async with self._cache_lock:
            hit = self._cache.get(key)
            if not hit:
                return None
            ts, val = hit
            if time.monotonic() - ts > float(ttl):
                del self._cache[key]
                return None
            return val

    async def _cache_put(self, key: str, value: IntentClassificationResult) -> None:
        ttl = int(self._settings.ai_intent_classifier_cache_ttl_seconds)
        if ttl <= 0:
            return
        async with self._cache_lock:
            max_e = int(self._settings.ai_intent_classifier_cache_max_entries)
            while len(self._cache) >= max_e:
                self._cache.pop(next(iter(self._cache)))
            self._cache[key] = (time.monotonic(), value)

    async def _record_intent_model_usage(
        self,
        ctx: IntentClassifierUsageContext | None,
        *,
        provider_name: str,
        model_name: str,
        norm_result: NormalizedAIResult | None,
        messages_for_estimate: tuple[ChatMessage, ...] | None,
        latency_ms: int,
        success: bool,
        error_code: str | None,
    ) -> None:
        if ctx is None or self._usage_logs is None:
            return
        t_usage = norm_result.tokens if norm_result else None
        ti, to, tt = normalize_usage(
            t_usage.input_tokens if t_usage else None,
            t_usage.output_tokens if t_usage else None,
            t_usage.total_tokens if t_usage else None,
        )
        used_est = False
        if tt == 0 and success and norm_result and (norm_result.text or "").strip() and messages_for_estimate:
            from app.ai_cost import estimate_tokens_from_messages

            ei, eo = estimate_tokens_from_messages(
                messages=messages_for_estimate,
                completion_text=norm_result.text or "",
                chars_per_token=self._settings.ai_token_chars_per_token_estimate,
            )
            if ei + eo > 0:
                ti, to, tt = ei, eo, ei + eo
                used_est = True

        catalog = build_pricing_catalog(self._settings)
        bd = calculate_cost(
            provider_name=provider_name,
            model_name=model_name,
            tokens_input=ti,
            tokens_output=to,
            tokens_total=tt,
            catalog=catalog,
            used_token_estimation=used_est,
        )
        await self._usage_logs.record(
            AIUsageLogPayload(
                bot_id=ctx.bot_id,
                conversation_id=ctx.conversation_id,
                message_id=None,
                provider_name=provider_name,
                model_name=model_name,
                tokens_input=bd.tokens_input,
                tokens_output=bd.tokens_output,
                tokens_total=bd.tokens_total,
                latency_ms=latency_ms,
                cost_usd=bd.cost_usd,
                success=success,
                error_code=error_code,
                step_kind=AI_USAGE_STEP_INTENT_CLASSIFIER,
            )
        )

    async def classify(
        self,
        user_message: str,
        *,
        niche_hint: str | None = None,
        use_ai_when_rules_miss: bool = True,
        sales_funnel_bot: bool = False,
        usage_context: IntentClassifierUsageContext | None = None,
    ) -> IntentClassificationResult:
        text = (user_message or "").strip()
        if not text:
            return IntentClassificationResult(
                intent=ConversationDetectedIntent.unknown,
                confidence=0.0,
                source="fallback",
            )

        ck = _cache_key(
            text,
            niche_hint,
            use_ai_when_rules_miss=use_ai_when_rules_miss,
            sales_funnel_bot=sales_funnel_bot,
        )
        cached = await self._cache_get(ck)
        if cached is not None:
            return cached

        ruled = classify_by_rules(text, niche_hint=niche_hint)
        if ruled is not None:
            intent, conf = ruled
            _SLOG.info(
                "intent_rules_hit",
                intent=intent.value,
                confidence=conf,
                niche_hint_set=bool((niche_hint or "").strip()),
            )
            out = IntentClassificationResult(intent=intent, confidence=conf, source="rules")
            await self._cache_put(ck, out)
            return out

        if not use_ai_when_rules_miss:
            if sales_funnel_bot:
                out = IntentClassificationResult(
                    intent=ConversationDetectedIntent.sales_interest,
                    confidence=0.55,
                    source="sales_default",
                )
            else:
                out = IntentClassificationResult(
                    intent=ConversationDetectedIntent.unknown,
                    confidence=0.25,
                    source="fallback",
                )
            _SLOG.debug(
                "intent_model_skipped",
                reason="use_ai_when_rules_miss=False",
                sales_funnel_bot=sales_funnel_bot,
                source=out.source,
            )
            await self._cache_put(ck, out)
            return out

        if (
            sales_funnel_bot
            and use_ai_when_rules_miss
            and self._settings.ai_sales_intent_gemini_ambiguity_only
            and not sales_intent_message_ambiguous_for_gemini(text)
        ):
            out = IntentClassificationResult(
                intent=ConversationDetectedIntent.sales_interest,
                confidence=0.55,
                source="sales_default",
            )
            _SLOG.debug(
                "intent_model_skipped",
                reason="ambiguity_only=True_and_not_ambiguous",
                text_len=len(text),
                source=out.source,
            )
            await self._cache_put(ck, out)
            return out

        provider = self._resolve_provider()
        if provider is None:
            _LOG.debug("intent_classifier_ai_skipped_no_provider")
            out = IntentClassificationResult(
                intent=ConversationDetectedIntent.unknown,
                confidence=0.3,
                source="fallback",
            )
            await self._cache_put(ck, out)
            return out

        user_block = (
            f"Classify this user message:\n{text[:4000]}"
            f"{_niche_line(niche_hint)}"
        )
        small_max = clamp_small_completion_budget(
            128,
            self._settings.ai_max_output_tokens_ceiling,
            floor=32,
        )
        params = GenerateParams(
            model=self._settings.gemini_default_model,
            messages=(
                ChatMessage(role="system", content=_SYSTEM_PROMPT),
                ChatMessage(role="user", content=user_block),
            ),
            temperature=0.0,
            max_output_tokens=small_max,
        )

        t0 = time.perf_counter()
        result: NormalizedAIResult | None = None
        model_called = False
        try:
            _SLOG.info(
                "intent_model_used",
                model=str(self._settings.gemini_default_model),
                sales_funnel_bot=sales_funnel_bot,
            )
            result = await provider.generate_response(params)
            model_called = True
        except Exception as exc:
            _LOG.warning("intent_classifier_ai_exception", exc_info=exc)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            await self._record_intent_model_usage(
                usage_context,
                provider_name="gemini",
                model_name=str(self._settings.gemini_default_model),
                norm_result=None,
                messages_for_estimate=None,
                latency_ms=latency_ms,
                success=False,
                error_code="intent_classifier_exception",
            )
            out = IntentClassificationResult(
                intent=ConversationDetectedIntent.unknown,
                confidence=0.25,
                source="fallback",
            )
            await self._cache_put(ck, out)
            return out
        finally:
            if isinstance(provider, GeminiProvider):
                await provider.aclose()
            if (
                model_called
                and usage_context is not None
                and usage_context.record_sales_llm_burst is not None
            ):
                try:
                    await usage_context.record_sales_llm_burst()
                except Exception:
                    _LOG.warning("intent_sales_llm_burst_record_failed", exc_info=True)

        latency_ms = int((time.perf_counter() - t0) * 1000)
        prov_name = (result.provider_name or "gemini").strip() or "gemini"
        log_model = (result.model_name or self._settings.gemini_default_model or "unknown").strip()

        if not result.success or not (result.text or "").strip():
            await self._record_intent_model_usage(
                usage_context,
                provider_name=prov_name,
                model_name=log_model,
                norm_result=result,
                messages_for_estimate=tuple(params.messages),
                latency_ms=latency_ms,
                success=False,
                error_code=result.error_code,
            )
            out = IntentClassificationResult(
                intent=ConversationDetectedIntent.unknown,
                confidence=0.3,
                source="fallback",
            )
            await self._cache_put(ck, out)
            return out

        await self._record_intent_model_usage(
            usage_context,
            provider_name=prov_name,
            model_name=log_model,
            norm_result=result,
            messages_for_estimate=tuple(params.messages),
            latency_ms=latency_ms,
            success=True,
            error_code=None,
        )

        payload = _extract_json_object(result.text)
        if payload is None:
            out = IntentClassificationResult(
                intent=ConversationDetectedIntent.unknown,
                confidence=0.35,
                source="fallback",
            )
            await self._cache_put(ck, out)
            return out

        label = payload.get("intent")
        intent = coerce_intent_label(str(label) if label is not None else "")
        conf = _confidence_from_payload(payload)

        if intent is None:
            out = IntentClassificationResult(
                intent=ConversationDetectedIntent.unknown,
                confidence=max(0.0, min(1.0, conf * 0.5)),
                source="gemini",
            )
            await self._cache_put(ck, out)
            return out

        if conf < _AI_CONFIDENCE_FLOOR:
            out = IntentClassificationResult(
                intent=ConversationDetectedIntent.unknown,
                confidence=conf,
                source="gemini",
            )
            await self._cache_put(ck, out)
            return out

        out = IntentClassificationResult(intent=intent, confidence=conf, source="gemini")
        await self._cache_put(ck, out)
        return out
