"""
End-to-end AI chat orchestration: persistence → prompt → provider → persistence → usage log.

Transaction boundaries:
    1. After the user message is flushed, :meth:`~app.repositories.ai_chat_repository.AIChatRepository.commit`
       runs before the provider call so the DB is not held open during network I/O.
    2. Assistant message + :class:`~app.models.ai_foundation.AIUsageLog` commit together after the call.

On provider failure, the user message remains stored; no assistant row is created; usage is still logged.

If :meth:`~app.ai_providers.base.AIProvider.generate_response` raises unexpectedly, the error is normalized
into a failure :class:`~app.ai_providers.types.NormalizedAIResult` and usage is still logged (no uncaught
leak past the service boundary).

Optional **knowledge RAG**: when ``knowledge_retrieval`` + ``knowledge_files`` are injected, the
service checks for ``ready`` knowledge files, runs retrieval + cost-aware context selection
(:class:`~app.services.knowledge_retrieval_service.KnowledgeRetrievalService`), formats excerpts via
:mod:`app.prompting.knowledge_excerpt`, and passes them through ``PromptExtensionContext.knowledge_excerpt``.
If nothing is ready, retrieval returns nothing, or enrichment fails, the model call proceeds without
knowledge. Provider code never sees retrieval types.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from time import perf_counter
from typing import Any, Literal, cast

from sqlalchemy.exc import SQLAlchemyError

from app.ai_cost import (
    build_pricing_catalog,
    calculate_cost,
    estimate_tokens_from_messages,
    normalize_usage,
)
from app.ai_providers.base import AIProvider
from app.ai_providers.registry import resolve_ai_provider
from app.ai_providers.types import GenerateParams, NormalizedAIResult, TokenUsage
from app.core.ai_generation_policy import resolve_max_output_tokens
from app.core.ai_pipeline_observability import (
    cache_type_for_step,
    estimate_tokens_saved_vs_llm,
    rough_token_estimate_chars_div4,
    track_ai_usage,
)
from app.core.config import Settings, get_settings
from app.core.error_tracking import capture_exception
from app.core.logging import get_logger
from app.integrations.telegram.lead_alert_target import EnvLeadTelegramAlertTargetProvider
from app.lib.chat_channels import CONVERSATION_CHANNEL_ADMIN_TEST
from app.models.bot import Bot
from app.models.user import User
from app.prompting.adapters import bot_to_prompt_source
from app.prompting.builder import build_chat_prompt
from app.prompting.slimming import prompt_build_options_for_user_text
from app.prompting.knowledge_excerpt import format_knowledge_context_excerpt
from app.prompting.types import HistoryTurn, PromptBuildInput, PromptExtensionContext
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.ai_usage_aggregate_repository import AIUsageAggregateRepository
from app.repositories.bot_repository import BotRepository
from app.repositories.knowledge_file_repository import KnowledgeFileRepository
from app.schemas.ai_chat import KnowledgeContextTurnMeta, SendBotMessageResult
from app.schemas.ai_usage import (
    AI_USAGE_STEP_EMBEDDING_FAILED,
    AI_USAGE_STEP_EXACT_CACHE,
    AI_USAGE_STEP_LLM_CALL,
    AI_USAGE_STEP_SEMANTIC_CACHE,
    AI_USAGE_STEP_TRIVIAL,
    AIUsageLogPayload,
)
from app.services.ai_error_taxonomy import classify_provider_error_code
from app.services.ai_exceptions import (
    AIServiceForbiddenError,
    AIServiceNotFoundError,
    AIServiceQuotaExceededError,
    AIServiceValidationError,
)
from app.services.ai_usage_log_service import AIUsageLogService
from app.services.ai_usage_quota_service import AIUsageQuotaService
from app.services.email_service import EmailService
from app.services.knowledge_retrieval_service import KnowledgeRetrievalService
from app.services.lead_owner_delivery_router import LeadOwnerDeliveryRouter
from app.services.sales_conversation_orchestrator import SalesConversationOrchestrator
from app.services.ai_chat_input_filter import handle_trivial_message, trivial_detection_normalized
from app.services.ai_completion_cache import remember_completion_caches, try_completion_cache
from app.services.semantic_completion_cache import SemanticCompletionCache, normalize_cache_message
from app.services.telegram_lead_alert_service import TelegramLeadAlertService

ProviderResolver = Callable[[Settings, str | None], AIProvider]

_LOG = get_logger("ai_service")


def _default_provider_resolver(settings: Settings, provider_id: str | None) -> AIProvider:
    return resolve_ai_provider(settings, provider_id)


def _conversation_state_str(conv: Any) -> str:
    raw = getattr(conv, "current_state", "") or ""
    v = getattr(raw, "value", raw)
    return str(v)[:128]


def _truncate_error_code(code: str | None, max_len: int = 64) -> str | None:
    if code is None:
        return None
    s = str(code).strip()
    return s[:max_len] if len(s) > max_len else s


def _finalize_completion_result(result: NormalizedAIResult) -> tuple[NormalizedAIResult, str | None]:
    """
    Treat success with no usable assistant text as ``invalid_response`` (no fake completion).

    Returns ``(result, truncated_error_code)`` for logging, usage rows, and API mapping.
    """
    error_code = _truncate_error_code(result.error_code)
    if result.success and not (result.text or "").strip():
        result = NormalizedAIResult(
            success=False,
            provider_name=result.provider_name,
            text=None,
            model_name=result.model_name,
            tokens=result.tokens,
            raw_usage=result.raw_usage,
            error_code="invalid_response",
            error_message=result.error_message,
        )
        error_code = _truncate_error_code(result.error_code)
    return result, error_code


_ENGAGEMENT_ENGINE_GOAL_TYPES: frozenset[str] = frozenset({"sales", "consulting"})
"""Goal types routed through the sales/engagement orchestrator (lead capture pipeline)."""


def _is_sales_goal(goal_type: str | None) -> bool:
    return (goal_type or "").strip().lower() in _ENGAGEMENT_ENGINE_GOAL_TYPES


class AIService:
    def __init__(
        self,
        chat_repo: AIChatRepository,
        bot_repo: BotRepository,
        *,
        settings: Settings | None = None,
        provider_resolver: ProviderResolver | None = None,
        usage_log_service: AIUsageLogService | None = None,
        sales_orchestrator: Any | None = None,
        knowledge_retrieval: KnowledgeRetrievalService | None = None,
        knowledge_files: KnowledgeFileRepository | None = None,
        usage_quota_repo: AIUsageAggregateRepository | None = None,
        semantic_cache: SemanticCompletionCache | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        self._chat = chat_repo
        self._bots = bot_repo
        self._settings = settings or get_settings()
        self._provider_resolver: ProviderResolver = provider_resolver or _default_provider_resolver
        self._usage_logs = usage_log_service or AIUsageLogService(chat_repo)
        self._sales_orchestrator = sales_orchestrator
        self._knowledge_retrieval = knowledge_retrieval
        self._knowledge_files = knowledge_files
        self._usage_quota_repo = usage_quota_repo
        self._semantic_cache: SemanticCompletionCache | None = (
            semantic_cache if semantic_cache is not None else SemanticCompletionCache.maybe_create(self._settings)
        )
        self._quota_svc: AIUsageQuotaService | None = (
            AIUsageQuotaService(usage_quota_repo, self._settings) if usage_quota_repo is not None else None
        )
        self._email_service = email_service

    async def _enforce_token_quotas(self, bot_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        daily = int(self._settings.ai_daily_total_tokens_soft_cap_per_bot)
        monthly = int(self._settings.ai_monthly_total_tokens_cap_per_owner)
        if daily <= 0 and monthly <= 0:
            return
        if self._quota_svc is None:
            if self._settings.deploy_environment_is_strict:
                _LOG.error(
                    "ai_usage_quota_repo_missing",
                    bot_id=str(bot_id),
                    owner_id=str(owner_id),
                    strict_env=True,
                    metric_event="ai_quota_misconfigured",
                )
                raise AIServiceQuotaExceededError(
                    "AI usage limits are active for this environment but quota tracking is unavailable.",
                    details={
                        "quota_scope": "configuration",
                        "measure": "tokens_total",
                        "retry_suggestion": "Retry later or contact support if this persists.",
                    },
                )
            return
        await self._quota_svc.assert_can_consume(bot_id=bot_id, owner_id=owner_id)

    async def _build_knowledge_context_for_prompt(
        self,
        *,
        user: User,
        bot_model: Bot,
        user_message: str,
        conversation_id: uuid.UUID,
    ) -> tuple[PromptExtensionContext | None, KnowledgeContextTurnMeta | None]:
        """
        Optional retrieval + budgeting + excerpt formatting. Never raises to callers.

        Returns ``(extensions, telemetry)``. Telemetry is ``None`` when knowledge integration is not wired.
        """
        if self._knowledge_retrieval is None or self._knowledge_files is None:
            return None, None

        try:
            n_ready = await self._knowledge_files.count_ready_knowledge_files_for_bot(
                owner_id=user.id,
                bot_id=bot_model.id,
            )
        except Exception:
            _LOG.warning(
                "ai_knowledge_ready_count_failed",
                exc_info=True,
                conversation_id=str(conversation_id),
                bot_id=str(bot_model.id),
            )
            return None, KnowledgeContextTurnMeta(had_ready_knowledge_files=False)

        if n_ready <= 0:
            return None, KnowledgeContextTurnMeta(had_ready_knowledge_files=False)

        try:
            frac = float(self._settings.ai_knowledge_chat_context_token_budget_fraction)
            base_tok = int(self._settings.knowledge_context_default_max_estimated_tokens)
            max_tok = max(64, min(int(base_tok * frac), self._settings.knowledge_context_max_estimated_tokens_ceiling))
            retrieval = await self._knowledge_retrieval.retrieve_for_bot(
                user,
                bot_model.id,
                query=user_message,
                limit=None,
                max_context_chunks=None,
                max_context_estimated_tokens=max_tok,
            )
        except Exception:
            _LOG.warning(
                "ai_knowledge_context_failed_gracefully",
                exc_info=True,
                conversation_id=str(conversation_id),
                bot_id=str(bot_model.id),
            )
            return None, KnowledgeContextTurnMeta(
                had_ready_knowledge_files=True,
                retrieval_hit_count=0,
                context_chunk_count=0,
                context_estimated_tokens=0,
            )

        cm = retrieval.context_meta
        meta = KnowledgeContextTurnMeta(
            had_ready_knowledge_files=True,
            retrieval_hit_count=len(retrieval.hits),
            context_chunk_count=cm.chunks_in_context if cm else 0,
            context_estimated_tokens=cm.total_estimated_tokens if cm else 0,
        )
        excerpt = format_knowledge_context_excerpt(retrieval.context)
        ext: PromptExtensionContext | None = None
        if excerpt:
            ext = PromptExtensionContext(knowledge_excerpt=excerpt)
        if meta.context_chunk_count > 0:
            _LOG.info(
                "ai_knowledge_context_injected",
                conversation_id=str(conversation_id),
                bot_id=str(bot_model.id),
                context_chunks=meta.context_chunk_count,
                context_estimated_tokens=meta.context_estimated_tokens,
                retrieval_hits=meta.retrieval_hit_count,
            )
        return ext, meta

    async def send_bot_message(
        self,
        bot: Bot,
        user: User,
        message_text: str,
        conversation_id: uuid.UUID | None = None,
    ) -> SendBotMessageResult:
        text = (message_text or "").strip()
        if not text:
            raise AIServiceValidationError("message_text must be non-empty")

        if bot.owner_id != user.id:
            raise AIServiceForbiddenError()

        bot_model = await self._bots.get_bot_by_id(owner_id=user.id, bot_id=bot.id)
        if bot_model is None:
            raise AIServiceForbiddenError()

        if bot_model.status == "archived":
            raise AIServiceValidationError("Cannot chat with an archived bot")

        await self._enforce_token_quotas(bot_model.id, user.id)

        try:
            if conversation_id is not None:
                conv = await self._chat.get_conversation_for_bot_owner(
                    conversation_id=conversation_id,
                    bot_id=bot_model.id,
                    owner_id=user.id,
                )
                if conv is None:
                    raise AIServiceNotFoundError()
            else:
                niche_snap = (bot_model.niche_id or "").strip() or None
                conv = await self._chat.create_conversation(
                    bot_id=bot_model.id,
                    owner_id=user.id,
                    niche_id_snapshot=niche_snap,
                    channel=CONVERSATION_CHANNEL_ADMIN_TEST,
                    visitor_client_hint=CONVERSATION_CHANNEL_ADMIN_TEST,
                )

            if _is_sales_goal(bot_model.goal_type):
                user_row = await self._chat.add_message(
                    conversation_id=conv.id,
                    bot_id=bot_model.id,
                    role="user",
                    content=text,
                )
                await self._chat.commit()
        except (AIServiceNotFoundError, AIServiceForbiddenError):
            raise
        except Exception as exc:
            await self._chat.rollback()
            raise AIServiceValidationError("Failed to persist user message") from exc

        if _is_sales_goal(bot_model.goal_type):
            if bool(self._settings.ai_pipeline_debug_trace_enabled):
                _LOG.info(
                    "ai_pipeline_debug",
                    phase="send_bot_message_branch",
                    path="sales_engine",
                    goal_type=bot_model.goal_type,
                    conversation_id=str(conv.id),
                    bot_id=str(bot_model.id),
                    trivial_flag=self._settings.ai_trivial_greeting_fast_path_enabled,
                )
            return await self._send_via_sales_engine(
                bot_model=bot_model,
                conv=conv,
                user=user,
                user_row_id=user_row.id,
                message_text=text,
            )

        # --- Non-sales: 5-layer pipeline (trivial → history → cache → prompt → LLM) ---
        cached_reply: str | None = None
        cache_hit_kind: str | None = None
        embedding_error: str | None = None
        try:
            dbg = bool(self._settings.ai_pipeline_debug_trace_enabled)
            if dbg:
                _LOG.info(
                    "ai_pipeline_debug",
                    phase="send_bot_message_branch",
                    path="non_sales_pipeline",
                    goal_type=bot_model.goal_type,
                    conversation_id=str(conv.id),
                    bot_id=str(bot_model.id),
                    trivial_flag=self._settings.ai_trivial_greeting_fast_path_enabled,
                )
            trivial_reply: str | None = None
            norm_trivial = trivial_detection_normalized(text)
            if dbg:
                _LOG.info(
                    "ai_pipeline_debug",
                    phase="before_handle_trivial_message",
                    conversation_id=str(conv.id),
                    normalized_inbound_for_trivial=norm_trivial,
                )
            if self._settings.ai_trivial_greeting_fast_path_enabled:
                trivial_reply = handle_trivial_message(text, bot_language=bot_model.language)
            if dbg:
                _LOG.info(
                    "ai_pipeline_debug",
                    phase="after_handle_trivial_message",
                    conversation_id=str(conv.id),
                    trivial_matched=trivial_reply is not None,
                )
            if trivial_reply is not None:
                user_row = await self._chat.add_message(
                    conversation_id=conv.id,
                    bot_id=bot_model.id,
                    role="user",
                    content=text,
                )
                await self._chat.commit()
                knowledge_meta = None
                t0 = perf_counter()
                latency_ms = int((perf_counter() - t0) * 1000)
                result = NormalizedAIResult(
                    success=True,
                    provider_name="internal",
                    text=trivial_reply,
                    model_name="trivial_filter",
                    tokens=TokenUsage(input_tokens=0, output_tokens=0, total_tokens=0),
                    raw_usage=None,
                    error_code=None,
                    error_message=None,
                )
                log_model = "trivial_filter"
                ti = to = tt = 0
                cost = None
                usage_step = AI_USAGE_STEP_TRIVIAL
                params: GenerateParams | None = None
                ec: str | None = None
                result, ec = _finalize_completion_result(result)
                failure_category = None
                used_est = False
                catalog = build_pricing_catalog(self._settings)
                bd = calculate_cost(
                    provider_name=result.provider_name,
                    model_name=log_model,
                    tokens_input=ti,
                    tokens_output=to,
                    tokens_total=tt,
                    catalog=catalog,
                    used_token_estimation=used_est,
                )
                cost = bd.cost_usd
                ti, to, tt = bd.tokens_input, bd.tokens_output, bd.tokens_total
                cpt = float(self._settings.ai_token_chars_per_token_estimate) or 4.0
                saved_est = estimate_tokens_saved_vs_llm(
                    user_text=text,
                    history_message_contents=(),
                    assistant_reply=(result.text or ""),
                    system_prompt_char_budget=int(self._settings.ai_pipeline_saved_tokens_system_chars),
                    chars_per_token=cpt,
                )
                track_ai_usage(
                    _LOG,
                    bot_id=bot_model.id,
                    conversation_id=conv.id,
                    channel=getattr(conv, "channel", None),
                    step_kind=usage_step,
                    provider_name=result.provider_name,
                    model_name=log_model,
                    input_tokens=ti,
                    output_tokens=to,
                    total_tokens=tt,
                    estimated_cost_usd=cost,
                    response_time_ms=latency_ms,
                    cache_type=cache_type_for_step(usage_step),
                    tokens_saved_est=saved_est,
                    success=result.success,
                    used_token_estimation=used_est,
                    error_code=ec,
                    failure_category=failure_category,
                )
                assistant_row_id: uuid.UUID | None = None
                assistant_text: str | None = result.text if result.success else None
                try:
                    if result.success and result.text:
                        assistant = await self._chat.add_message(
                            conversation_id=conv.id,
                            bot_id=bot_model.id,
                            role="assistant",
                            content=result.text,
                            model_name=log_model,
                            tokens_input=ti if ti else None,
                            tokens_output=to if to else None,
                            tokens_total=tt if tt else None,
                            latency_ms=latency_ms,
                            cost_usd=cost,
                        )
                        assistant_row_id = assistant.id
                    await self._usage_logs.record(
                        AIUsageLogPayload(
                            bot_id=bot_model.id,
                            conversation_id=conv.id,
                            message_id=assistant_row_id,
                            provider_name=result.provider_name,
                            model_name=log_model,
                            tokens_input=ti,
                            tokens_output=to,
                            tokens_total=tt,
                            latency_ms=latency_ms,
                            cost_usd=cost,
                            success=result.success,
                            error_code=ec if not result.success else None,
                            step_kind=usage_step,
                        )
                    )
                    await self._chat.touch_conversation_updated_at(conv.id)
                    await self._chat.commit()
                except SQLAlchemyError as exc:
                    await self._chat.rollback()
                    _LOG.error(
                        "ai_chat_persistence_failed_after_provider",
                        exc_info=True,
                        conversation_id=str(conv.id),
                        bot_id=str(bot_model.id),
                        provider_success=result.success,
                    )
                    capture_exception(
                        exc,
                        domain="ai_persistence",
                        tags={
                            "conversation_id": str(conv.id),
                            "bot_id": str(bot_model.id),
                            "provider_success": str(result.success),
                        },
                    )
                    return SendBotMessageResult(
                        conversation_id=conv.id,
                        user_message_id=user_row.id,
                        assistant_message_id=assistant_row_id,
                        assistant_text=assistant_text,
                        model_name=log_model if result.success else None,
                        success=False,
                        error_code="persistence_error",
                        error_message="Failed to save assistant message or usage log.",
                        error_category=classify_provider_error_code("persistence_error"),
                        latency_ms=latency_ms,
                        tokens_input=ti if ti else None,
                        tokens_output=to if ti else None,
                        tokens_total=tt if ti else None,
                        cost_usd=cost,
                        knowledge_context=knowledge_meta,
                    )
                return SendBotMessageResult(
                    conversation_id=conv.id,
                    user_message_id=user_row.id,
                    assistant_message_id=assistant_row_id,
                    assistant_text=assistant_text,
                    model_name=log_model if result.success else None,
                    success=result.success,
                    error_code=ec if not result.success else None,
                    error_message=result.error_message if not result.success else None,
                    error_category=failure_category,
                    latency_ms=latency_ms,
                    tokens_input=ti if ti else None,
                    tokens_output=to if to else None,
                    tokens_total=tt if ti else None,
                    cost_usd=cost,
                    knowledge_context=knowledge_meta,
                )

            knowledge_ext, knowledge_meta = await self._build_knowledge_context_for_prompt(
                user=user,
                bot_model=bot_model,
                user_message=text,
                conversation_id=conv.id,
            )
            knowledge_in_prompt = bool(
                knowledge_meta is not None and int(getattr(knowledge_meta, "context_chunk_count", 0) or 0) > 0
            )
            prompt_opts = prompt_build_options_for_user_text(
                self._settings, text, knowledge_injected=knowledge_in_prompt
            )
            history_rows = await self._chat.list_recent_history_messages(
                conversation_id=conv.id,
                limit=prompt_opts.max_history_messages,
            )
            st = _conversation_state_str(conv)
            t0 = perf_counter()
            cached_reply, cache_hit_kind, embedding_error = await try_completion_cache(
                self._semantic_cache,
                self._settings,
                bot_id=bot_model.id,
                conversation_state=st,
                raw_text=text,
                knowledge_injected=knowledge_in_prompt,
            )

            user_row = await self._chat.add_message(
                conversation_id=conv.id,
                bot_id=bot_model.id,
                role="user",
                content=text,
            )
            await self._chat.commit()
        except SQLAlchemyError as exc:
            await self._chat.rollback()
            raise AIServiceValidationError("Failed to persist user message") from exc

        history_turns = tuple(
            HistoryTurn(
                role=cast(Literal["user", "assistant"], m.role),
                content=m.content,
            )
            for m in history_rows
            if m.role in ("user", "assistant")
        )

        raw_model = (bot_model.model_name or "").strip()
        max_out = resolve_max_output_tokens(
            bot_max_output_tokens=bot_model.max_output_tokens,
            ceiling=self._settings.ai_max_output_tokens_ceiling,
            default_when_unset=self._settings.ai_max_output_tokens_default,
        )

        latency_ms = int((perf_counter() - t0) * 1000)

        provider: AIProvider | None = None
        params: GenerateParams | None = None
        resolved_model = raw_model or "unknown"

        if cached_reply is not None:
            model_name_hit = "exact_cache_hit" if cache_hit_kind == "exact" else "semantic_cache_hit"
            result = NormalizedAIResult(
                success=True,
                provider_name="gemini",
                text=cached_reply,
                model_name=model_name_hit,
                tokens=TokenUsage(input_tokens=0, output_tokens=0, total_tokens=0),
                raw_usage=None,
                error_code=None,
                error_message=None,
            )
        elif embedding_error:
            _LOG.error(
                "ai_chat_embedding_blocked_llm",
                conversation_id=str(conv.id),
                bot_id=str(bot_model.id),
                embedding_error_code=embedding_error,
                semantic_embedding_model=str(self._settings.ai_semantic_cache_embedding_model),
            )
            result = NormalizedAIResult(
                success=False,
                provider_name="gemini",
                text=None,
                model_name=str(self._settings.ai_semantic_cache_embedding_model),
                tokens=None,
                raw_usage=None,
                error_code="embedding_failed",
                error_message="Embedding service failed. Try again shortly.",
            )
        else:
            pkg = build_chat_prompt(
                PromptBuildInput(
                    bot=bot_to_prompt_source(bot_model),
                    user_message=text,
                    history=history_turns,
                    options=prompt_opts,
                    extensions=knowledge_ext,
                ),
                use_knowledge=(False if not knowledge_in_prompt else None),
                is_short=prompt_opts.slim_system_prompt,
            )
            provider = self._provider_resolver(
                self._settings,
                (bot_model.provider_name or "").strip() or None,
            )
            resolved_model = raw_model or provider.default_model
            params = GenerateParams(
                model=resolved_model,
                messages=pkg.as_provider_messages(),
                temperature=bot_model.temperature,
                max_output_tokens=max_out,
            )
            if bool(self._settings.ai_pipeline_debug_trace_enabled):
                _LOG.info(
                    "ai_pipeline_debug",
                    phase="before_provider_generate_response",
                    path="non_sales",
                    conversation_id=str(conv.id),
                    bot_id=str(bot_model.id),
                    model=resolved_model,
                )
            t_llm = perf_counter()
            try:
                result = await provider.generate_response(params)
            except Exception as exc:
                ec, em = provider.normalize_error(exc)
                result = NormalizedAIResult(
                    success=False,
                    provider_name=provider.provider_name,
                    text=None,
                    model_name=resolved_model,
                    error_code=ec,
                    error_message=em,
                )
            latency_ms = int((perf_counter() - t_llm) * 1000)

        if provider is not None:
            await provider.aclose()
        log_model = (result.model_name or "").strip() or resolved_model or "unknown"
        result, ec = _finalize_completion_result(result)

        failure_category: str | None = None
        if not result.success:
            failure_category = classify_provider_error_code(ec)

        t_usage = result.tokens
        ti, to, tt = normalize_usage(
            t_usage.input_tokens if t_usage else None,
            t_usage.output_tokens if t_usage else None,
            t_usage.total_tokens if t_usage else None,
        )
        used_est = False
        if (
            cache_hit_kind is None
            and tt == 0
            and result.success
            and result.text
            and params is not None
        ):
            ei, eo = estimate_tokens_from_messages(
                messages=params.messages,
                completion_text=result.text,
                chars_per_token=self._settings.ai_token_chars_per_token_estimate,
            )
            if ei + eo > 0:
                ti, to, tt = ei, eo, ei + eo
                used_est = True
        cpt_llm = float(self._settings.ai_token_chars_per_token_estimate) or 4.0
        if cache_hit_kind is None and result.success and (result.text or "").strip() and tt == 0:
            to = max(to, rough_token_estimate_chars_div4(result.text or "", chars_per_token=cpt_llm))
            if params is not None:
                pc = sum(len(m.content or "") for m in params.messages)
                if pc > 0:
                    ti = max(ti, int(pc / cpt_llm))
            tt = ti + to
            if tt > 0:
                used_est = True

        catalog = build_pricing_catalog(self._settings)
        bd = calculate_cost(
            provider_name=result.provider_name,
            model_name=log_model,
            tokens_input=ti,
            tokens_output=to,
            tokens_total=tt,
            catalog=catalog,
            used_token_estimation=used_est,
        )
        cost = bd.cost_usd
        ti, to, tt = bd.tokens_input, bd.tokens_output, bd.tokens_total

        if embedding_error:
            usage_step = AI_USAGE_STEP_EMBEDDING_FAILED
        elif cache_hit_kind == "semantic":
            usage_step = AI_USAGE_STEP_SEMANTIC_CACHE
        elif cache_hit_kind == "exact":
            usage_step = AI_USAGE_STEP_EXACT_CACHE
        else:
            usage_step = AI_USAGE_STEP_LLM_CALL

        hist_contents = [str(getattr(m, "content", "") or "") for m in history_rows]
        tokens_saved_est: int | None = None
        if usage_step in (AI_USAGE_STEP_SEMANTIC_CACHE, AI_USAGE_STEP_EXACT_CACHE):
            tokens_saved_est = estimate_tokens_saved_vs_llm(
                user_text=text,
                history_message_contents=hist_contents,
                assistant_reply=(result.text or ""),
                system_prompt_char_budget=int(self._settings.ai_pipeline_saved_tokens_system_chars),
                chars_per_token=cpt_llm,
            )

        track_ai_usage(
            _LOG,
            bot_id=bot_model.id,
            conversation_id=conv.id,
            channel=getattr(conv, "channel", None),
            step_kind=usage_step,
            provider_name=result.provider_name,
            model_name=log_model,
            input_tokens=ti,
            output_tokens=to,
            total_tokens=tt,
            estimated_cost_usd=cost,
            response_time_ms=latency_ms,
            cache_type=cache_type_for_step(usage_step),
            tokens_saved_est=tokens_saved_est,
            success=result.success,
            used_token_estimation=used_est,
            error_code=ec,
            failure_category=failure_category,
        )

        if (
            cache_hit_kind is None
            and result.success
            and (result.text or "").strip()
            and self._semantic_cache is not None
        ):
            norm = normalize_cache_message(text)
            st = _conversation_state_str(conv)
            try:
                await remember_completion_caches(
                    self._semantic_cache,
                    self._settings,
                    bot_id=bot_model.id,
                    conversation_state=st,
                    raw_user_text=text,
                    normalized_message=norm,
                    response_text=(result.text or "").strip(),
                    knowledge_injected=knowledge_in_prompt,
                )
            except Exception:
                _LOG.warning("completion_cache_remember_failed", exc_info=True, bot_id=str(bot_model.id))

        assistant_row_id: uuid.UUID | None = None
        assistant_text: str | None = result.text if result.success else None

        try:
            if result.success and result.text:
                assistant = await self._chat.add_message(
                    conversation_id=conv.id,
                    bot_id=bot_model.id,
                    role="assistant",
                    content=result.text,
                    model_name=log_model,
                    tokens_input=ti if ti else None,
                    tokens_output=to if to else None,
                    tokens_total=tt if tt else None,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                )
                assistant_row_id = assistant.id

            await self._usage_logs.record(
                AIUsageLogPayload(
                    bot_id=bot_model.id,
                    conversation_id=conv.id,
                    message_id=assistant_row_id,
                    provider_name=result.provider_name,
                    model_name=log_model,
                    tokens_input=ti,
                    tokens_output=to,
                    tokens_total=tt,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                    success=result.success,
                    error_code=ec if not result.success else None,
                    step_kind=usage_step,
                )
            )
            await self._chat.touch_conversation_updated_at(conv.id)
            await self._chat.commit()
        except SQLAlchemyError as exc:
            await self._chat.rollback()
            _LOG.error(
                "ai_chat_persistence_failed_after_provider",
                exc_info=True,
                conversation_id=str(conv.id),
                bot_id=str(bot_model.id),
                provider_success=result.success,
            )
            capture_exception(
                exc,
                domain="ai_persistence",
                tags={
                    "conversation_id": str(conv.id),
                    "bot_id": str(bot_model.id),
                    "provider_success": str(result.success),
                },
            )
            return SendBotMessageResult(
                conversation_id=conv.id,
                user_message_id=user_row.id,
                assistant_message_id=assistant_row_id,
                assistant_text=assistant_text,
                model_name=log_model if result.success else None,
                success=False,
                error_code="persistence_error",
                error_message="Failed to save assistant message or usage log.",
                error_category=classify_provider_error_code("persistence_error"),
                latency_ms=latency_ms,
                tokens_input=ti if ti else None,
                tokens_output=to if to else None,
                tokens_total=tt if tt else None,
                cost_usd=cost,
                knowledge_context=knowledge_meta,
            )

        return SendBotMessageResult(
            conversation_id=conv.id,
            user_message_id=user_row.id,
            assistant_message_id=assistant_row_id,
            assistant_text=assistant_text,
            model_name=log_model if result.success else None,
            success=result.success,
            error_code=ec if not result.success else None,
            error_message=result.error_message if not result.success else None,
            error_category=failure_category,
            latency_ms=latency_ms,
            tokens_input=ti if ti else None,
            tokens_output=to if to else None,
            tokens_total=tt if tt else None,
            cost_usd=cost,
            knowledge_context=knowledge_meta,
        )

    async def _send_via_sales_engine(
        self,
        *,
        bot_model: Bot,
        conv: Any,
        user: User,
        user_row_id: uuid.UUID,
        message_text: str,
    ) -> SendBotMessageResult:
        """
        Sales bots: full turn via :class:`~app.services.sales_conversation_orchestrator.SalesConversationOrchestrator`.

        The user message is already persisted and committed; the orchestrator loads history from the repository.
        """
        orch = self._sales_orchestrator or SalesConversationOrchestrator(
            self._chat,
            self._bots,
            settings=self._settings,
            provider_resolver=self._provider_resolver,
            usage_log_service=self._usage_logs,
            lead_owner_delivery=LeadOwnerDeliveryRouter(
                telegram_alerts=TelegramLeadAlertService(
                    EnvLeadTelegramAlertTargetProvider(self._settings),
                ),
                email_service=self._email_service,
            ),
            semantic_cache=self._semantic_cache,
        )
        turn = await orch.process_sales_turn(
            bot_model,
            conv,
            message_text,
            owner_user=user,
            persist_user_message=False,
        )
        ec = _truncate_error_code(turn.error_code)
        err_cat = turn.metadata.failure_category if not turn.success else None
        if err_cat is None and ec is not None:
            err_cat = classify_provider_error_code(ec)
        return SendBotMessageResult(
            conversation_id=turn.conversation_id,
            user_message_id=user_row_id,
            assistant_message_id=turn.assistant_message_id,
            assistant_text=turn.assistant_text,
            model_name=turn.model_name,
            success=turn.success,
            error_code=ec,
            error_message=turn.error_message,
            error_category=err_cat,
            latency_ms=turn.latency_ms,
            tokens_input=turn.tokens_input,
            tokens_output=turn.tokens_output,
            tokens_total=turn.tokens_total,
            cost_usd=turn.cost_usd,
        )
