"""
**Sales conversation orchestration** — one entry point per user turn before the chat model.

**Flow (per turn)**
    1. Persist user message (caller may do this earlier; we support pre-inserted history).
    2. Classify intent (:class:`~app.services.intent_classifier_service.IntentClassifierService`).
    3. Resolve niche flow + extract structured slots from the user text (target field from
       ``__orch_target_field`` set on the previous assistant turn).
    4. Run question planner *before* transition to apply completion flags into collected data.
    5. Run state machine transition.
    6. Run question planner again for the *post-transition* state (prompt + next target).
    7. Build response plan + prompt extensions (does not modify :mod:`app.prompting.builder`).
    8. Call provider; persist assistant row, usage, and updated conversation columns.

**Separation**
    * Planner → state machine → response strategy share one pipeline:
      :func:`_run_planner_transition_pipeline` (single place for that contract).
    * :meth:`SalesConversationOrchestrator.process_sales_turn` sequences guards, extraction, that pipeline,
      optional **CRM lead capture** (:mod:`app.services.sales_lead_capture_turn`), prompt build, and provider I/O.
    * When gates pass, ``collected_data_json`` gains ``__lead_capture_done`` / ``__captured_lead_id``;
      optional owner delivery (dashboard stamp + Telegram + future channels) runs **after** commit
      via :class:`~app.services.lead_owner_delivery_router.LeadOwnerDeliveryRouter`.

Internal JSON keys (orchestrator-owned, not niche core_fields):

* ``__orch_target_field`` — last field the assistant asked for (drives extraction next turn).
* ``_qp_clar_round`` — clarification question index for :mod:`app.services.question_planner`.
* ``__lead_capture_done`` / ``__captured_lead_id`` — set by :mod:`app.services.sales_lead_capture_turn`
  after a CRM lead exists for this conversation (idempotent; avoids duplicate inserts).
* ``_sf_*`` — safeguard counters (rate, identical-input streaks, slot-miss / vague streaks); see
  :mod:`app.services.sales_safeguards`.

**Lead capture trigger:** immediately after :func:`_run_planner_transition_pipeline` returns
(``next_state`` + final ``collected``). If gates pass, the orchestrator may skip the chat model and
persist a closing confirmation instead; owner delivery runs only after a successful commit.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from time import perf_counter
from typing import TYPE_CHECKING, Literal, cast

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
from app.lib.niche_flow.registry import get_niche_conversation_flow_or_generic
from app.lib.niche_flow.schema import NicheConversationFlowDefinition
from app.lib.niche_registry import get_niche_by_id
from app.models.ai_foundation import Conversation
from app.models.bot import Bot
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.prompting.adapters import bot_to_prompt_source
from app.prompting.builder import build_prompt_package
from app.prompting.slimming import prompt_build_options_for_user_text
from app.prompting.types import HistoryTurn, PromptBuildInput, PromptExtensionContext
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.bot_repository import BotRepository
from app.repositories.lead_repository import LeadRepository
from app.schemas.ai_usage import (
    AI_USAGE_STEP_EMBEDDING_FAILED,
    AI_USAGE_STEP_EXACT_CACHE,
    AI_USAGE_STEP_LLM_CALL,
    AI_USAGE_STEP_SEMANTIC_CACHE,
    AI_USAGE_STEP_SYNTHETIC_OUTPUT,
    AI_USAGE_STEP_TRIVIAL,
    AIUsageLogPayload,
)
from app.services.ai_error_taxonomy import classify_provider_error_code
from app.services.ai_exceptions import AIServiceValidationError
from app.services.ai_usage_log_service import AIUsageLogService
from app.services.ai_chat_input_filter import handle_trivial_message, trivial_detection_normalized
from app.services.ai_completion_cache import remember_completion_caches, try_completion_cache
from app.integrations.providers.gemini_errors import RATE_LIMITED as _GEMINI_RATE_LIMITED
from app.services.semantic_completion_cache import SemanticCompletionCache, normalize_cache_message
from app.services.collected_data_extraction import (
    CollectedDataMergeOutcome,
    apply_user_reply_to_collected_data,
)
from app.services.conversation_state_machine import (
    LatestUserMessageMeta,
    StateMachineInput,
    StateTransitionResult,
    coerce_conversation_state,
    transition_state,
)
from app.services.intent_classifier_service import IntentClassifierService
from app.services.sales_llm_burst_limiter import SalesLLMBurstLimiter
from app.services.intent_types import IntentClassificationResult, IntentClassifierUsageContext
from app.services.lead_owner_delivery_router import LeadOwnerDeliveryRouter
from app.services.question_planner import QuestionPlannerInput, QuestionPlannerResult, plan_next_question
from app.services.response_planner import ResponsePlannerInput, ResponseStrategy, plan_response_strategy
from app.services.sales_lead_capture_turn import (
    SalesPipelineLeadCaptureResult,
    run_sales_lead_capture_after_pipeline,
)
from app.services.sales_safeguards import (
    effective_routing_intent,
    evaluate_early_turn_guards,
    evaluate_post_extraction_guards,
)

if TYPE_CHECKING:
    from app.models.user import User

_LOG = get_logger("sales_orchestrator")

ORCH_TARGET_FIELD_KEY = "__orch_target_field"
QP_CLAR_ROUND_KEY = "_qp_clar_round"


def _conversation_state_str(conv: Conversation) -> str:
    raw = getattr(conv, "current_state", "") or ""
    v = getattr(raw, "value", raw)
    return str(v)[:128]


ProviderResolver = Callable[[Settings, str | None], AIProvider]


def _default_provider_resolver(settings: Settings, provider_id: str | None) -> AIProvider:
    return resolve_ai_provider(settings, provider_id)


@dataclass(frozen=True, slots=True)
class SalesTurnLeadHints:
    """Non-persisted snapshot for analytics; CRM rows are created in :mod:`app.services.sales_lead_capture_turn`."""

    niche_id: str
    core_field_snapshot: dict[str, object]
    funnel_state: str
    qualification_complete: bool
    all_core_fields_collected: bool


@dataclass(frozen=True, slots=True)
class SalesTurnMetadata:
    """Auditable metadata for analytics and future pipelines."""

    detected_intent: str
    intent_confidence: float
    intent_source: str
    previous_state: str
    next_state: str
    state_rule_id: str
    state_transition_reason: str
    question_planner_action: str
    question_planner_reason: str
    response_mode: str
    response_strategy_reason: str
    extraction_keys_written: tuple[str, ...]
    extraction_audit: tuple[str, ...]
    lead_hints: SalesTurnLeadHints
    failure_category: str | None = None
    safeguard_reason_code: str | None = None
    """Set when a canned safeguard reply was used instead of the chat model."""
    lead_capture_created: bool = False
    """True when a new ``leads`` row was inserted this turn (not duplicate)."""
    lead_capture_lead_id: uuid.UUID | None = None
    lead_capture_reason: str | None = None
    """Last :class:`~app.services.lead_creation_service.LeadCreationResult` reason from capture attempt."""


@dataclass(frozen=True, slots=True)
class SalesTurnResult:
    assistant_text: str | None
    success: bool
    conversation_id: uuid.UUID
    updated_current_state: str
    updated_collected_data: dict[str, object]
    metadata: SalesTurnMetadata
    user_message_id: uuid.UUID | None
    assistant_message_id: uuid.UUID | None
    model_name: str | None
    error_code: str | None
    error_message: str | None
    latency_ms: int
    tokens_input: int | None
    tokens_output: int | None
    tokens_total: int | None
    cost_usd: Decimal | None


def _read_clarification_round(collected: dict[str, object]) -> int:
    raw = collected.get(QP_CLAR_ROUND_KEY, 0)
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def _read_extraction_target(collected: dict[str, object]) -> str | None:
    raw = collected.get(ORCH_TARGET_FIELD_KEY)
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def _apply_completion_flags_from_planner(
    collected: dict[str, object],
    qp: QuestionPlannerResult,
) -> None:
    if qp.suggest_set_qualification_complete:
        collected["qualification_complete"] = True
    if qp.suggest_set_clarification_complete:
        collected["clarification_complete"] = True


def _sync_orchestrator_keys_after_prompt_plan(
    collected: dict[str, object],
    *,
    next_state: ConversationFlowState,
    qp: QuestionPlannerResult,
) -> None:
    if qp.target_field_key:
        collected[ORCH_TARGET_FIELD_KEY] = qp.target_field_key
    else:
        collected.pop(ORCH_TARGET_FIELD_KEY, None)

    if next_state == ConversationFlowState.clarification:
        collected[QP_CLAR_ROUND_KEY] = qp.next_clarification_round
    else:
        collected.pop(QP_CLAR_ROUND_KEY, None)


def _core_field_snapshot(
    collected: dict[str, object],
    core_keys: frozenset[str],
) -> dict[str, object]:
    return {k: collected[k] for k in core_keys if k in collected}


def _compose_lead_flow_hint(
    *,
    response_mode: str,
    talking_points: tuple[str, ...],
    next_question: str | None,
    tone_hints: tuple[str, ...],
    target_field: str | None,
) -> str:
    lines = [
        f"Response mode: {response_mode}",
        f"Tone hints: {', '.join(tone_hints)}",
    ]
    if talking_points:
        lines.append("Key points to cover briefly:")
        lines.extend(f"- {p}" for p in talking_points[:5])
    if next_question:
        lines.append(
            "Include exactly one natural question toward the user (do not add extra questions): "
            f"{next_question}"
        )
    if target_field:
        lines.append(f"If you ask a question, it should help elicit: `{target_field}`.")
    return "\n".join(lines)


def _finalize_ai_result(result: NormalizedAIResult) -> tuple[NormalizedAIResult, str | None]:
    raw_ec = result.error_code
    ec = raw_ec[:64] if raw_ec else None
    if result.success and not (result.text or "").strip():
        return (
            NormalizedAIResult(
                success=False,
                provider_name=result.provider_name,
                text=None,
                model_name=result.model_name,
                tokens=result.tokens,
                raw_usage=result.raw_usage,
                error_code="invalid_response",
                error_message=result.error_message,
            ),
            "invalid_response",
        )
    return result, ec


def _run_planner_transition_pipeline(
    *,
    conv: Conversation,
    collected: dict[str, object],
    flow: NicheConversationFlowDefinition,
    niche_id: str,
    routing_intent: ConversationDetectedIntent,
    user_text: str,
    core_keys: frozenset[str],
) -> tuple[StateTransitionResult, QuestionPlannerResult, ResponseStrategy, SalesTurnLeadHints]:
    """
    One deterministic funnel step: pre-transition question plan (completion hints) → state machine
    → post-transition question plan → sync ``__orch_target_field`` / ``_qp_clar_round`` → response strategy.

    Mutates ``collected`` in place. Used for both LLM turns and safeguard (canned) turns so behavior stays aligned.
    """
    state_before, _ = coerce_conversation_state(conv.current_state)
    clar_r = _read_clarification_round(collected)
    qp_pre = plan_next_question(
        QuestionPlannerInput(
            niche_flow=flow,
            current_state=state_before,
            collected_data=collected,
            detected_intent=routing_intent,
            clarification_round=clar_r,
            collect_optional_core_fields=False,
        ),
    )
    _apply_completion_flags_from_planner(collected, qp_pre)

    msg_meta = LatestUserMessageMeta(is_empty=False, char_length=len(user_text))
    trans = transition_state(
        StateMachineInput(
            current_state=state_before,
            detected_intent=routing_intent,
            collected_data=collected,
            niche_context=niche_id,
            latest_user_message=msg_meta,
            recent_states=None,
        ),
    )
    next_state = trans.next_state

    qp_after = plan_next_question(
        QuestionPlannerInput(
            niche_flow=flow,
            current_state=next_state,
            collected_data=collected,
            detected_intent=routing_intent,
            clarification_round=_read_clarification_round(collected),
            collect_optional_core_fields=False,
        ),
    )
    _sync_orchestrator_keys_after_prompt_plan(collected, next_state=next_state, qp=qp_after)

    r_strategy = plan_response_strategy(
        ResponsePlannerInput(
            niche_flow=flow,
            current_state=next_state,
            detected_intent=routing_intent,
            question_plan=qp_after,
            collected_data=collected,
        ),
    )

    lead_hints = SalesTurnLeadHints(
        niche_id=flow.niche_id,
        core_field_snapshot=_core_field_snapshot(collected, core_keys),
        funnel_state=next_state.value,
        qualification_complete=bool(collected.get("qualification_complete")),
        all_core_fields_collected=qp_after.all_core_fields_collected,
    )
    return trans, qp_after, r_strategy, lead_hints


class SalesConversationOrchestrator:
    """
    Wires classifier → extraction → state machine → planners → prompt → provider → persistence.

    Construct per request with a shared :class:`~sqlalchemy.ext.asyncio.AsyncSession` (via repo).
    """

    def __init__(
        self,
        chat_repo: AIChatRepository,
        bot_repo: BotRepository,
        *,
        settings: Settings | None = None,
        intent_classifier: IntentClassifierService | None = None,
        provider_resolver: ProviderResolver | None = None,
        usage_log_service: AIUsageLogService | None = None,
        lead_repo: LeadRepository | None = None,
        lead_owner_delivery: LeadOwnerDeliveryRouter | None = None,
        semantic_cache: SemanticCompletionCache | None = None,
        burst_limiter: SalesLLMBurstLimiter | None = None,
    ) -> None:
        self._chat = chat_repo
        self._bots = bot_repo
        self._settings = settings or get_settings()
        self._usage_logs = usage_log_service or AIUsageLogService(chat_repo)
        self._intent = intent_classifier or IntentClassifierService(
            settings=self._settings,
            usage_log_service=self._usage_logs,
        )
        self._provider_resolver = provider_resolver or _default_provider_resolver
        self._lead_repo = lead_repo or LeadRepository(chat_repo.session)
        self._lead_owner_delivery = lead_owner_delivery
        self._semantic_cache = semantic_cache
        self._burst = burst_limiter or SalesLLMBurstLimiter.from_settings(self._settings)

    async def _route_lead_owner_delivery_after_commit_if_needed(
        self,
        *,
        owner_user: "User | None",
        bot_model: Bot,
        capture: SalesPipelineLeadCaptureResult,
    ) -> None:
        notify = capture.notify_telegram
        lead = capture.lead_for_telegram
        if (
            owner_user is not None
            and notify
            and lead is not None
            and self._lead_owner_delivery is not None
        ):
            await self._lead_owner_delivery.route_new_lead_after_commit(
                self._chat.session,
                owner_id=owner_user.id,
                owner_user=owner_user,
                bot=bot_model,
                lead=lead,
            )

    async def _complete_safeguard_turn(
        self,
        *,
        bot_model: Bot,
        conv: Conversation,
        text: str,
        collected: dict[str, object],
        user_row_id: uuid.UUID | None,
        flow: NicheConversationFlowDefinition,
        niche_id: str,
        core_keys: frozenset[str],
        routing_intent: ConversationDetectedIntent,
        ic: IntentClassificationResult,
        extract_out: CollectedDataMergeOutcome,
        canned_assistant_text: str,
        safeguard_reason_code: str,
        owner_user: "User | None" = None,
    ) -> SalesTurnResult:
        """
        Finish the turn with a **canned** assistant message (no chat model).

        Still runs the question planner and state machine so the funnel can recover politely.
        """
        collected = dict(collected)
        trans, qp_after, r_strategy, lead_hints = _run_planner_transition_pipeline(
            conv=conv,
            collected=collected,
            flow=flow,
            niche_id=niche_id,
            routing_intent=routing_intent,
            user_text=text,
            core_keys=core_keys,
        )
        next_state = trans.next_state

        capture = await run_sales_lead_capture_after_pipeline(
            lead_repo=self._lead_repo,
            bot=bot_model,
            owner_user=owner_user,
            conversation=conv,
            collected=collected,
            next_state=next_state,
            routing_intent=routing_intent,
            last_user_message=text,
        )
        if capture.skip_provider and capture.closing_assistant_text:
            assistant_text = capture.closing_assistant_text.strip()
            log_model = "lead_capture_closing"
        else:
            assistant_text = (canned_assistant_text or "").strip() or (
                "Let me help you get unstuck — what would you like to do next?"
            )
            log_model = "safeguard_canned"

        latency_ms = 0
        ti, to, tt = 0, 0, 0
        catalog = build_pricing_catalog(self._settings)
        bd = calculate_cost(
            provider_name="safeguard",
            model_name=log_model,
            tokens_input=ti,
            tokens_output=to,
            tokens_total=tt,
            catalog=catalog,
            used_token_estimation=False,
        )
        cost = bd.cost_usd

        metadata = SalesTurnMetadata(
            detected_intent=routing_intent.value,
            intent_confidence=ic.confidence,
            intent_source=ic.source,
            previous_state=trans.previous_state.value,
            next_state=next_state.value,
            state_rule_id=trans.rule_id,
            state_transition_reason=trans.reason,
            question_planner_action=qp_after.action.value,
            question_planner_reason=qp_after.planner_reason_code,
            response_mode=r_strategy.response_mode.value,
            response_strategy_reason=r_strategy.strategy_reason_code,
            extraction_keys_written=extract_out.keys_written,
            extraction_audit=extract_out.audit_trail,
            lead_hints=lead_hints,
            failure_category=None,
            safeguard_reason_code=safeguard_reason_code,
            lead_capture_created=capture.created_new_lead,
            lead_capture_lead_id=(
                capture.lead_for_telegram.id
                if capture.lead_for_telegram is not None and capture.created_new_lead
                else None
            ),
            lead_capture_reason=capture.creation_reason,
        )

        assistant_row_id: uuid.UUID | None = None
        try:
            await self._chat.update_conversation_sales_flow(
                conv.id,
                current_state=next_state.value,
                detected_intent=routing_intent.value,
                collected_data_json=collected,
            )
            assistant = await self._chat.add_message(
                conversation_id=conv.id,
                bot_id=bot_model.id,
                role="assistant",
                content=assistant_text,
                model_name=log_model,
                tokens_input=None,
                tokens_output=None,
                tokens_total=None,
                latency_ms=latency_ms,
                cost_usd=cost,
            )
            assistant_row_id = assistant.id

            await self._usage_logs.record(
                AIUsageLogPayload(
                    bot_id=bot_model.id,
                    conversation_id=conv.id,
                    message_id=assistant_row_id,
                    provider_name="safeguard",
                    model_name=log_model,
                    tokens_input=ti,
                    tokens_output=to,
                    tokens_total=tt,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                    success=True,
                    error_code=None,
                ),
            )
            await self._chat.touch_conversation_updated_at(conv.id)
            await self._chat.commit()
        except SQLAlchemyError as exc:
            await self._chat.rollback()
            _LOG.error(
                "sales_turn_safeguard_persistence_failed",
                exc_info=True,
                conversation_id=str(conv.id),
            )
            capture_exception(
                exc,
                domain="ai_sales_persistence",
                tags={"conversation_id": str(conv.id), "phase": "safeguard"},
            )
            return SalesTurnResult(
                assistant_text=assistant_text,
                success=False,
                conversation_id=conv.id,
                updated_current_state=next_state.value,
                updated_collected_data=collected,
                metadata=metadata,
                user_message_id=user_row_id,
                assistant_message_id=assistant_row_id,
                model_name=None,
                error_code="persistence_error",
                error_message="Failed to persist safeguard reply.",
                latency_ms=latency_ms,
                tokens_input=None,
                tokens_output=None,
                tokens_total=None,
                cost_usd=cost,
            )

        conv.current_state = next_state.value
        conv.detected_intent = routing_intent.value
        conv.collected_data_json = collected

        await self._route_lead_owner_delivery_after_commit_if_needed(
            owner_user=owner_user,
            bot_model=bot_model,
            capture=capture,
        )

        _LOG.info(
            "sales_safeguard_canned_reply",
            conversation_id=str(conv.id),
            reason=safeguard_reason_code,
        )

        return SalesTurnResult(
            assistant_text=assistant_text,
            success=True,
            conversation_id=conv.id,
            updated_current_state=next_state.value,
            updated_collected_data=collected,
            metadata=metadata,
            user_message_id=user_row_id,
            assistant_message_id=assistant_row_id,
            model_name=log_model,
            error_code=None,
            error_message=None,
            latency_ms=latency_ms,
            tokens_input=ti,
            tokens_output=to,
            tokens_total=tt,
            cost_usd=cost,
        )

    async def _complete_trivial_greeting_turn(
        self,
        *,
        bot_model: Bot,
        conv: Conversation,
        text: str,
        collected: dict[str, object],
        user_row_id: uuid.UUID | None,
        flow: NicheConversationFlowDefinition,
        niche_id: str,
        core_keys: frozenset[str],
        trivial_reply: str,
        owner_user: "User | None" = None,
    ) -> SalesTurnResult:
        """Finish a sales turn with a canned greeting (no intent classifier or chat model)."""
        collected = dict(collected)
        ic = IntentClassificationResult(
            intent=ConversationDetectedIntent.unknown,
            confidence=1.0,
            source="trivial_fast_path",
        )
        extract_out = CollectedDataMergeOutcome(
            collected_data=dict(collected),
            proposed_extractions={},
            keys_written=(),
            audit_trail=("trivial_skip_extract",),
        )
        trans, qp_after, r_strategy, lead_hints = _run_planner_transition_pipeline(
            conv=conv,
            collected=collected,
            flow=flow,
            niche_id=niche_id,
            routing_intent=ConversationDetectedIntent.unknown,
            user_text=text,
            core_keys=core_keys,
        )
        next_state = trans.next_state

        capture = await run_sales_lead_capture_after_pipeline(
            lead_repo=self._lead_repo,
            bot=bot_model,
            owner_user=owner_user,
            conversation=conv,
            collected=collected,
            next_state=next_state,
            routing_intent=ConversationDetectedIntent.unknown,
            last_user_message=text,
        )
        if capture.skip_provider and capture.closing_assistant_text:
            assistant_text = capture.closing_assistant_text.strip()
            log_model = "lead_capture_closing"
        else:
            assistant_text = (trivial_reply or "").strip() or (
                "Let me help you get unstuck — what would you like to do next?"
            )
            log_model = "trivial_filter"

        _LOG.info(
            "trivial_skipped_llm",
            conversation_id=str(conv.id),
            bot_id=str(bot_model.id),
            skip_reason="trivial_greeting",
            inbound_chars=len(text),
        )

        latency_ms = 0
        ti, to, tt = 0, 0, 0
        catalog = build_pricing_catalog(self._settings)
        bd = calculate_cost(
            provider_name="internal",
            model_name=log_model,
            tokens_input=ti,
            tokens_output=to,
            tokens_total=tt,
            catalog=catalog,
            used_token_estimation=False,
        )
        cost = bd.cost_usd

        metadata = SalesTurnMetadata(
            detected_intent=ConversationDetectedIntent.unknown.value,
            intent_confidence=ic.confidence,
            intent_source=ic.source,
            previous_state=trans.previous_state.value,
            next_state=next_state.value,
            state_rule_id=trans.rule_id,
            state_transition_reason=trans.reason,
            question_planner_action=qp_after.action.value,
            question_planner_reason=qp_after.planner_reason_code,
            response_mode=r_strategy.response_mode.value,
            response_strategy_reason=r_strategy.strategy_reason_code,
            extraction_keys_written=extract_out.keys_written,
            extraction_audit=extract_out.audit_trail,
            lead_hints=lead_hints,
            failure_category=None,
            safeguard_reason_code="trivial_greeting_fast_path",
            lead_capture_created=capture.created_new_lead,
            lead_capture_lead_id=(
                capture.lead_for_telegram.id
                if capture.lead_for_telegram is not None and capture.created_new_lead
                else None
            ),
            lead_capture_reason=capture.creation_reason,
        )

        assistant_row_id: uuid.UUID | None = None
        try:
            await self._chat.update_conversation_sales_flow(
                conv.id,
                current_state=next_state.value,
                detected_intent=ConversationDetectedIntent.unknown.value,
                collected_data_json=collected,
            )
            assistant = await self._chat.add_message(
                conversation_id=conv.id,
                bot_id=bot_model.id,
                role="assistant",
                content=assistant_text,
                model_name=log_model,
                tokens_input=None,
                tokens_output=None,
                tokens_total=None,
                latency_ms=latency_ms,
                cost_usd=cost,
            )
            assistant_row_id = assistant.id

            await self._usage_logs.record(
                AIUsageLogPayload(
                    bot_id=bot_model.id,
                    conversation_id=conv.id,
                    message_id=assistant_row_id,
                    provider_name="internal",
                    model_name=log_model,
                    tokens_input=ti,
                    tokens_output=to,
                    tokens_total=tt,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                    success=True,
                    error_code=None,
                    step_kind=AI_USAGE_STEP_TRIVIAL,
                ),
            )
            await self._chat.touch_conversation_updated_at(conv.id)
            await self._chat.commit()
        except SQLAlchemyError as exc:
            await self._chat.rollback()
            _LOG.error(
                "sales_turn_trivial_persistence_failed",
                exc_info=True,
                conversation_id=str(conv.id),
            )
            capture_exception(
                exc,
                domain="ai_sales_persistence",
                tags={"conversation_id": str(conv.id), "phase": "trivial_greeting"},
            )
            return SalesTurnResult(
                assistant_text=assistant_text,
                success=False,
                conversation_id=conv.id,
                updated_current_state=next_state.value,
                updated_collected_data=collected,
                metadata=metadata,
                user_message_id=user_row_id,
                assistant_message_id=assistant_row_id,
                model_name=None,
                error_code="persistence_error",
                error_message="Failed to persist trivial greeting reply.",
                latency_ms=latency_ms,
                tokens_input=None,
                tokens_output=None,
                tokens_total=None,
                cost_usd=cost,
            )

        conv.current_state = next_state.value
        conv.detected_intent = ConversationDetectedIntent.unknown.value
        conv.collected_data_json = collected

        await self._route_lead_owner_delivery_after_commit_if_needed(
            owner_user=owner_user,
            bot_model=bot_model,
            capture=capture,
        )

        cpt_sales = float(self._settings.ai_token_chars_per_token_estimate) or 4.0
        saved_est = estimate_tokens_saved_vs_llm(
            user_text=text,
            history_message_contents=(),
            assistant_reply=assistant_text,
            system_prompt_char_budget=int(self._settings.ai_pipeline_saved_tokens_system_chars),
            chars_per_token=cpt_sales,
        )
        track_ai_usage(
            _LOG,
            bot_id=bot_model.id,
            conversation_id=conv.id,
            channel=getattr(conv, "channel", None),
            step_kind=AI_USAGE_STEP_TRIVIAL,
            provider_name="internal",
            model_name=log_model,
            input_tokens=ti,
            output_tokens=to,
            total_tokens=tt,
            estimated_cost_usd=cost,
            response_time_ms=latency_ms,
            cache_type=cache_type_for_step(AI_USAGE_STEP_TRIVIAL),
            tokens_saved_est=saved_est,
            success=True,
            used_token_estimation=False,
            error_code=None,
            failure_category=None,
        )

        _LOG.info(
            "sales_trivial_greeting_fast_path",
            conversation_id=str(conv.id),
        )

        return SalesTurnResult(
            assistant_text=assistant_text,
            success=True,
            conversation_id=conv.id,
            updated_current_state=next_state.value,
            updated_collected_data=collected,
            metadata=metadata,
            user_message_id=user_row_id,
            assistant_message_id=assistant_row_id,
            model_name=log_model,
            error_code=None,
            error_message=None,
            latency_ms=latency_ms,
            tokens_input=ti,
            tokens_output=to,
            tokens_total=tt,
            cost_usd=cost,
        )

    async def process_sales_turn(
        self,
        bot: Bot,
        conversation: Conversation,
        user_message: str,
        *,
        owner_user: "User | None" = None,
        persist_user_message: bool = True,
    ) -> SalesTurnResult:
        """
        Run the full sales turn. Validates bot/conversation ownership when ``owner_user`` is passed.

        When ``persist_user_message`` is True, appends the user row and commits before the
        provider call (same boundary as :class:`~app.services.ai_service.AIService`).
        """
        text = (user_message or "").strip()
        if not text:
            raise AIServiceValidationError("user_message must be non-empty")

        if owner_user is not None:
            if bot.owner_id != owner_user.id or conversation.owner_id != owner_user.id:
                raise AIServiceValidationError("Bot/conversation owner mismatch")
            if conversation.bot_id != bot.id:
                raise AIServiceValidationError("Conversation does not belong to this bot")

        if bot.status == "archived":
            raise AIServiceValidationError("Cannot chat with an archived bot")

        bot_model = await self._bots.get_bot_by_id(owner_id=bot.owner_id, bot_id=bot.id)
        if bot_model is None:
            raise AIServiceValidationError("Bot not found")

        conv = conversation
        prompt_opts = prompt_build_options_for_user_text(self._settings, text)
        history_rows = await self._chat.list_recent_history_messages(
            conversation_id=conv.id,
            limit=prompt_opts.max_history_messages,
        )
        history_turns = tuple(
            HistoryTurn(
                role=cast(Literal["user", "assistant"], m.role),
                content=m.content,
            )
            for m in history_rows
            if m.role in ("user", "assistant")
        )

        user_row_id: uuid.UUID | None = None
        try:
            if persist_user_message:
                user_row = await self._chat.add_message(
                    conversation_id=conv.id,
                    bot_id=bot_model.id,
                    role="user",
                    content=text,
                )
                user_row_id = user_row.id
                await self._chat.commit()
        except SQLAlchemyError as exc:
            await self._chat.rollback()
            raise AIServiceValidationError("Failed to persist user message") from exc

        niche_id = (bot_model.niche_id or "").strip() or (conv.niche_id_snapshot or "") or "generic"
        flow = get_niche_conversation_flow_or_generic(niche_id)
        core_keys = frozenset(f.key for f in flow.core_fields)

        collected: dict[str, object] = dict(conv.collected_data_json or {})
        extraction_target = _read_extraction_target(collected)

        early = evaluate_early_turn_guards(text, collected)
        if early is not None:
            ic_unknown = IntentClassificationResult(
                intent=ConversationDetectedIntent.unknown,
                confidence=0.0,
                source="fallback",
            )
            ex_empty = CollectedDataMergeOutcome(
                collected_data=dict(collected),
                proposed_extractions={},
                keys_written=(),
                audit_trail=("safeguard:early_skip_extract",),
            )
            return await self._complete_safeguard_turn(
                bot_model=bot_model,
                conv=conv,
                text=text,
                collected=dict(collected),
                user_row_id=user_row_id,
                flow=flow,
                niche_id=niche_id,
                core_keys=core_keys,
                routing_intent=ConversationDetectedIntent.unknown,
                ic=ic_unknown,
                extract_out=ex_empty,
                canned_assistant_text=early.canned_user_message
                or "Let me help you get unstuck — what would you like to do next?",
                safeguard_reason_code=early.reason_code,
                owner_user=owner_user,
            )

        dbg_trace = bool(self._settings.ai_pipeline_debug_trace_enabled)
        if dbg_trace:
            _LOG.info(
                "ai_pipeline_debug",
                phase="sales_before_trivial",
                conversation_id=str(conv.id),
                bot_id=str(bot_model.id),
                trivial_flag=self._settings.ai_trivial_greeting_fast_path_enabled,
                inbound_chars=len(text),
            )
        norm_trivial = trivial_detection_normalized(text)
        if dbg_trace:
            _LOG.info(
                "ai_pipeline_debug",
                phase="before_handle_trivial_message",
                conversation_id=str(conv.id),
                normalized_inbound_for_trivial=norm_trivial,
            )
        trivial_reply: str | None = None
        if self._settings.ai_trivial_greeting_fast_path_enabled:
            trivial_reply = handle_trivial_message(text, bot_language=bot_model.language)
        if dbg_trace:
            _LOG.info(
                "ai_pipeline_debug",
                phase="after_handle_trivial_message",
                conversation_id=str(conv.id),
                trivial_matched=trivial_reply is not None,
            )
        if trivial_reply is not None:
            return await self._complete_trivial_greeting_turn(
                bot_model=bot_model,
                conv=conv,
                text=text,
                collected=dict(collected),
                user_row_id=user_row_id,
                flow=flow,
                niche_id=niche_id,
                core_keys=core_keys,
                trivial_reply=trivial_reply,
                owner_user=owner_user,
            )

        async def _burst_after_intent() -> None:
            await self._burst.record_llm_invocation(bot_model.id)

        ic = await self._intent.classify(
            text,
            niche_hint=_niche_hint(bot_model.niche_id),
            use_ai_when_rules_miss=self._settings.ai_sales_use_model_for_intent_when_rules_miss,
            sales_funnel_bot=True,
            usage_context=IntentClassifierUsageContext(
                bot_id=bot_model.id,
                conversation_id=conv.id,
                record_sales_llm_burst=_burst_after_intent,
            ),
        )
        routing_intent = effective_routing_intent(ic)

        extract_out = apply_user_reply_to_collected_data(
            collected,
            text,
            flow,
            target_field_key=extraction_target,
        )
        collected = dict(extract_out.collected_data)

        post = evaluate_post_extraction_guards(
            text,
            extraction_target=extraction_target,
            keys_written=extract_out.keys_written,
            collected=collected,
        )
        if post is not None:
            return await self._complete_safeguard_turn(
                bot_model=bot_model,
                conv=conv,
                text=text,
                collected=dict(collected),
                user_row_id=user_row_id,
                flow=flow,
                niche_id=niche_id,
                core_keys=core_keys,
                routing_intent=routing_intent,
                ic=ic,
                extract_out=extract_out,
                canned_assistant_text=post.canned_user_message
                or "Let me help you get unstuck — what would you like to do next?",
                safeguard_reason_code=post.reason_code,
                owner_user=owner_user,
            )

        intent = routing_intent

        trans, qp_after, r_strategy, lead_hints = _run_planner_transition_pipeline(
            conv=conv,
            collected=collected,
            flow=flow,
            niche_id=niche_id,
            routing_intent=intent,
            user_text=text,
            core_keys=core_keys,
        )
        next_state = trans.next_state

        capture = await run_sales_lead_capture_after_pipeline(
            lead_repo=self._lead_repo,
            bot=bot_model,
            owner_user=owner_user,
            conversation=conv,
            collected=collected,
            next_state=next_state,
            routing_intent=intent,
            last_user_message=text,
        )

        lead_flow = _compose_lead_flow_hint(
            response_mode=r_strategy.response_mode.value,
            talking_points=r_strategy.key_talking_points,
            next_question=r_strategy.next_question,
            tone_hints=r_strategy.tone_hints,
            target_field=qp_after.target_field_key,
        )

        params: GenerateParams | None = None
        cache_hit_kind: str | None = None
        usage_step: str = AI_USAGE_STEP_LLM_CALL
        if capture.skip_provider and capture.closing_assistant_text:
            assistant_text_precheck = capture.closing_assistant_text.strip()
            result = NormalizedAIResult(
                success=True,
                provider_name="lead_capture",
                text=assistant_text_precheck,
                model_name="lead_capture_closing",
                tokens=None,
                raw_usage=None,
                error_code=None,
                error_message=None,
            )
            latency_ms = 0
            log_model = "lead_capture_closing"
            usage_step = AI_USAGE_STEP_SYNTHETIC_OUTPUT
            result, ec = _finalize_ai_result(result)
            provider = self._provider_resolver(
                self._settings,
                (bot_model.provider_name or "").strip() or None,
            )
            await provider.aclose()
        else:
            provider = self._provider_resolver(
                self._settings,
                (bot_model.provider_name or "").strip() or None,
            )
            raw_model = (bot_model.model_name or "").strip()
            resolved_model = raw_model or provider.default_model
            max_out = resolve_max_output_tokens(
                bot_max_output_tokens=bot_model.max_output_tokens,
                ceiling=self._settings.ai_max_output_tokens_ceiling,
                default_when_unset=self._settings.ai_max_output_tokens_default,
            )

            t0 = perf_counter()
            cached_reply, cache_hit_kind, embedding_error = await try_completion_cache(
                self._semantic_cache,
                self._settings,
                bot_id=bot_model.id,
                conversation_state=_conversation_state_str(conv),
                raw_text=text,
                knowledge_injected=False,
            )

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
                latency_ms = int((perf_counter() - t0) * 1000)
            elif embedding_error:
                _LOG.error(
                    "sales_embedding_blocked_llm",
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
                latency_ms = int((perf_counter() - t0) * 1000)
                params = None
                usage_step = AI_USAGE_STEP_EMBEDDING_FAILED
            else:
                if await self._burst.should_skip_chat_llm_for_burst(
                    bot_model.id,
                    text,
                    bot_language=bot_model.language,
                ):
                    fb_busy = (self._settings.ai_telegram_gemini_rate_limit_user_message_uz or "").strip()
                    result = NormalizedAIResult(
                        success=True,
                        provider_name="internal",
                        text=fb_busy or "One moment — please try again shortly.",
                        model_name="burst_opening_fallback",
                        tokens=TokenUsage(input_tokens=0, output_tokens=0, total_tokens=0),
                        raw_usage=None,
                        error_code=None,
                        error_message=None,
                    )
                    _LOG.info(
                        "trivial_skipped_llm",
                        conversation_id=str(conv.id),
                        bot_id=str(bot_model.id),
                        skip_reason="burst_window",
                    )
                    latency_ms = int((perf_counter() - t0) * 1000)
                    params = None
                    usage_step = AI_USAGE_STEP_SYNTHETIC_OUTPUT
                else:
                    pkg = build_prompt_package(
                        PromptBuildInput(
                            bot=bot_to_prompt_source(bot_model),
                            user_message=text,
                            history=history_turns,
                            options=prompt_opts,
                            extensions=PromptExtensionContext(lead_flow_hint=lead_flow),
                        ),
                    )
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
                            conversation_id=str(conv.id),
                            bot_id=str(bot_model.id),
                            model=resolved_model,
                            cache_miss=True,
                        )
                    try:
                        result = await provider.generate_response(params)
                    except Exception as exc:
                        ec_gen, em = provider.normalize_error(exc)
                        result = NormalizedAIResult(
                            success=False,
                            provider_name=provider.provider_name,
                            text=None,
                            model_name=resolved_model,
                            error_code=ec_gen,
                            error_message=em,
                        )
                    finally:
                        await self._burst.record_llm_invocation(bot_model.id)
                    latency_ms = int((perf_counter() - t0) * 1000)
            await provider.aclose()

            log_model = result.model_name or resolved_model or "unknown"
            result, ec = _finalize_ai_result(result)

            if (
                cache_hit_kind is None
                and params is not None
                and (not result.success)
                and (ec or "").strip() == _GEMINI_RATE_LIMITED
            ):
                fb_rl = (self._settings.ai_telegram_gemini_rate_limit_user_message_uz or "").strip()
                if fb_rl:
                    _LOG.info(
                        "telegram_rate_limit_fallback",
                        conversation_id=str(conv.id),
                        bot_id=str(bot_model.id),
                        channel=getattr(conv, "channel", None),
                    )
                    result = NormalizedAIResult(
                        success=True,
                        provider_name=result.provider_name or "gemini",
                        text=fb_rl,
                        model_name="telegram_rate_limit_fallback",
                        tokens=TokenUsage(input_tokens=0, output_tokens=0, total_tokens=0),
                        raw_usage=None,
                        error_code=None,
                        error_message=None,
                    )
                    log_model = "telegram_rate_limit_fallback"
                    result, ec = _finalize_ai_result(result)
                    usage_step = AI_USAGE_STEP_SYNTHETIC_OUTPUT

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
        cpt_sales = float(self._settings.ai_token_chars_per_token_estimate) or 4.0
        if cache_hit_kind is None and result.success and (result.text or "").strip() and tt == 0:
            to = max(to, rough_token_estimate_chars_div4(result.text or "", chars_per_token=cpt_sales))
            if params is not None:
                pc = sum(len(m.content or "") for m in params.messages)
                if pc > 0:
                    ti = max(ti, int(pc / cpt_sales))
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

        if usage_step not in (AI_USAGE_STEP_SYNTHETIC_OUTPUT, AI_USAGE_STEP_EMBEDDING_FAILED):
            if cache_hit_kind == "semantic":
                usage_step = AI_USAGE_STEP_SEMANTIC_CACHE
            elif cache_hit_kind == "exact":
                usage_step = AI_USAGE_STEP_EXACT_CACHE
            else:
                usage_step = AI_USAGE_STEP_LLM_CALL

        hist_sales = [t.content for t in history_turns]
        tokens_saved_est_sales: int | None = None
        if usage_step in (AI_USAGE_STEP_SEMANTIC_CACHE, AI_USAGE_STEP_EXACT_CACHE):
            tokens_saved_est_sales = estimate_tokens_saved_vs_llm(
                user_text=text,
                history_message_contents=hist_sales,
                assistant_reply=(result.text or ""),
                system_prompt_char_budget=int(self._settings.ai_pipeline_saved_tokens_system_chars),
                chars_per_token=cpt_sales,
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
            tokens_saved_est=tokens_saved_est_sales,
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
                    knowledge_injected=False,
                )
            except Exception:
                _LOG.warning("completion_cache_remember_failed", exc_info=True, bot_id=str(bot_model.id))

        _LOG.info(
            "sales_turn_ai_cost_breakdown",
            conversation_id=str(conv.id),
            bot_id=str(bot_model.id),
            intent_source=ic.source,
            intent_label=intent.value,
            chat_step_skipped=bool(capture.skip_provider),
            chat_tokens_total=int(tt) if tt else 0,
            chat_cost_usd=str(cost) if cost is not None else None,
            chat_provider=(result.provider_name or "").strip() or None,
        )

        assistant_text = result.text if result.success else None
        assistant_row_id: uuid.UUID | None = None

        metadata = SalesTurnMetadata(
            detected_intent=intent.value,
            intent_confidence=ic.confidence,
            intent_source=ic.source,
            previous_state=trans.previous_state.value,
            next_state=next_state.value,
            state_rule_id=trans.rule_id,
            state_transition_reason=trans.reason,
            question_planner_action=qp_after.action.value,
            question_planner_reason=qp_after.planner_reason_code,
            response_mode=r_strategy.response_mode.value,
            response_strategy_reason=r_strategy.strategy_reason_code,
            extraction_keys_written=extract_out.keys_written,
            extraction_audit=extract_out.audit_trail,
            lead_hints=lead_hints,
            failure_category=failure_category,
            safeguard_reason_code=None,
            lead_capture_created=capture.created_new_lead,
            lead_capture_lead_id=(
                capture.lead_for_telegram.id
                if capture.lead_for_telegram is not None and capture.created_new_lead
                else None
            ),
            lead_capture_reason=capture.creation_reason,
        )

        try:
            await self._chat.update_conversation_sales_flow(
                conv.id,
                current_state=next_state.value,
                detected_intent=intent.value,
                collected_data_json=collected,
            )
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
                ),
            )
            await self._chat.touch_conversation_updated_at(conv.id)
            await self._chat.commit()
        except SQLAlchemyError as exc:
            await self._chat.rollback()
            _LOG.error(
                "sales_turn_persistence_failed",
                exc_info=True,
                conversation_id=str(conv.id),
            )
            capture_exception(
                exc,
                domain="ai_sales_persistence",
                tags={"conversation_id": str(conv.id), "phase": "main_turn"},
            )
            return SalesTurnResult(
                assistant_text=assistant_text,
                success=False,
                conversation_id=conv.id,
                updated_current_state=next_state.value,
                updated_collected_data=collected,
                metadata=metadata,
                user_message_id=user_row_id,
                assistant_message_id=assistant_row_id,
                model_name=log_model if result.success else None,
                error_code="persistence_error",
                error_message="Failed to persist conversation or assistant message.",
                latency_ms=latency_ms,
                tokens_input=ti if ti else None,
                tokens_output=to if to else None,
                tokens_total=tt if tt else None,
                cost_usd=cost,
            )

        conv.current_state = next_state.value
        conv.detected_intent = intent.value
        conv.collected_data_json = collected

        await self._route_lead_owner_delivery_after_commit_if_needed(
            owner_user=owner_user,
            bot_model=bot_model,
            capture=capture,
        )

        return SalesTurnResult(
            assistant_text=assistant_text,
            success=result.success,
            conversation_id=conv.id,
            updated_current_state=next_state.value,
            updated_collected_data=collected,
            metadata=metadata,
            user_message_id=user_row_id,
            assistant_message_id=assistant_row_id,
            model_name=log_model if result.success else None,
            error_code=ec if not result.success else None,
            error_message=result.error_message if not result.success else None,
            latency_ms=latency_ms,
            tokens_input=ti if ti else None,
            tokens_output=to if to else None,
            tokens_total=tt if tt else None,
            cost_usd=cost,
        )


def _niche_hint(niche_id: str) -> str | None:
    nd = get_niche_by_id((niche_id or "").strip())
    if nd is None:
        return None
    return (nd.short_description or "").strip() or None


__all__ = [
    "ORCH_TARGET_FIELD_KEY",
    "QP_CLAR_ROUND_KEY",
    "SalesConversationOrchestrator",
    "SalesTurnLeadHints",
    "SalesTurnMetadata",
    "SalesTurnResult",
]
