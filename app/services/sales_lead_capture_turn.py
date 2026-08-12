"""
**Sales turn → CRM lead capture** — single integration point for the orchestrator.

Triggered **once per turn** after the planner/state-machine pipeline, using the same eligibility rules
as :class:`~app.services.lead_creation_service.LeadCreationService` plus a JSON flag so we do not
re-hit the database every turn after capture.

**Channels:** ``Lead.source_channel`` mirrors :attr:`~app.models.ai_foundation.Conversation.channel``
(``web_widget``, ``telegram``, ``admin_test``, …). Telegram conversations use this same module; optional
``telegram_username`` / ``telegram_first_name`` hints in ``collected_data_json`` come from the webhook
adapter, not a parallel CRM stack.

Orchestrator-owned keys in ``collected_data_json``:

* ``__lead_capture_done`` — ``True`` once a lead row exists (created this session or duplicate).
* ``__captured_lead_id`` — string UUID for dashboards / debugging.

Telegram alerts run **after** the chat transaction commits; the orchestrator calls
:class:`~app.services.telegram_lead_alert_service.TelegramLeadAlertService` only when
``notify_telegram`` is true on :class:`SalesPipelineLeadCaptureResult` (new inserts only).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.telegram_channel_events import TELEGRAM_LEAD_CREATED, emit_telegram_channel_event
from app.lib.chat_channels import CONVERSATION_CHANNEL_TELEGRAM
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.repositories.lead_event_repository import LeadEventRepository
from app.repositories.lead_repository import LeadRepository
from app.services.lead_creation_service import (
    LEAD_CAPTURE_DUPLICATE_MERGE_REASONS,
    LEAD_CAPTURE_IDEMPOTENCY_REASONS,
    LeadCreationService,
    extract_phone_for_lead,
)
from app.services.lead_event_service import LeadEventService
from app.services.lead_scoring import score_lead
from app.services.lead_summary import generate_lead_summary

if TYPE_CHECKING:
    from app.models.ai_foundation import Conversation
    from app.models.bot import Bot
    from app.models.lead import Lead
    from app.models.user import User

LEAD_CAPTURE_DONE_KEY = "__lead_capture_done"
CAPTURED_LEAD_ID_KEY = "__captured_lead_id"


@dataclass(slots=True)
class SalesPipelineLeadCaptureResult:
    """Outcome of :func:`run_sales_lead_capture_after_pipeline` for one turn."""

    skip_provider: bool
    """If true, orchestrator should not call the chat model (closing message already chosen)."""

    closing_assistant_text: str | None
    """Non-empty when ``skip_provider`` (fresh lead created this turn)."""

    collected_mutated: bool
    """True when capture flags were merged into ``collected``."""

    created_new_lead: bool
    notify_telegram: bool
    """True only for a **new** insert this turn (no duplicate alerts)."""

    lead_for_telegram: "Lead | None"
    creation_reason: str | None


def is_lead_capture_marked_done(collected: dict[str, object]) -> bool:
    return bool(collected.get(LEAD_CAPTURE_DONE_KEY))


def _mark_capture_done(collected: dict[str, object], lead_id: uuid.UUID) -> None:
    collected[LEAD_CAPTURE_DONE_KEY] = True
    collected[CAPTURED_LEAD_ID_KEY] = str(lead_id)


def format_lead_capture_closing_message(*, bot_name: str, summary_line: str) -> str:
    name = (bot_name or "").strip() or "our team"
    line = (summary_line or "").strip()
    if line:
        return (
            f"Thank you — we have everything we need and saved your details. "
            f"{line}\n\nSomeone from {name} will follow up with you shortly."
        )
    return (
        f"Thank you — we have everything we need and saved your details. "
        f"Someone from {name} will follow up with you shortly."
    )


async def run_sales_lead_capture_after_pipeline(
    *,
    lead_repo: LeadRepository,
    bot: "Bot",
    owner_user: "User | None",
    conversation: "Conversation",
    collected: dict[str, object],
    next_state: ConversationFlowState,
    routing_intent: ConversationDetectedIntent,
    last_user_message: str,
) -> SalesPipelineLeadCaptureResult:
    """
    Evaluate gates and optionally insert a lead row **before** the assistant reply is finalized.

    Mutates ``collected`` when capture succeeds or when a duplicate lead already exists (idempotent flag).
    """
    if owner_user is None:
        return SalesPipelineLeadCaptureResult(
            skip_provider=False,
            closing_assistant_text=None,
            collected_mutated=False,
            created_new_lead=False,
            notify_telegram=False,
            lead_for_telegram=None,
            creation_reason=None,
        )

    if is_lead_capture_marked_done(collected):
        return SalesPipelineLeadCaptureResult(
            skip_provider=False,
            closing_assistant_text=None,
            collected_mutated=False,
            created_new_lead=False,
            notify_telegram=False,
            lead_for_telegram=None,
            creation_reason=None,
        )

    phone = extract_phone_for_lead(collected, None)
    score_res = score_lead(
        niche_id=(conversation.niche_id_snapshot or bot.niche_id or "generic"),
        detected_intent=routing_intent.value,
        collected_data_json=collected,
        phone=phone,
        conversation_state=next_state.value,
    )
    summary = generate_lead_summary(
        niche_id=(conversation.niche_id_snapshot or bot.niche_id or "generic"),
        collected_data_json=collected,
        conversation_state=next_state.value,
        recent_user_messages=((last_user_message,) if (last_user_message or "").strip() else None),
    )

    event_svc = LeadEventService(LeadEventRepository(lead_repo.session))
    creation = LeadCreationService(lead_repo, events=event_svc)
    res = await creation.try_create_lead_from_conversation(
        bot=bot,
        owner=owner_user,
        conversation=conversation,
        collected_data_json=collected,
        lead_score=score_res.score,
        lead_temperature=score_res.temperature,
        summary=summary,
        source_channel=(conversation.channel or "").strip() or None,
        explicit_phone=None,
        funnel_state_override=next_state.value,
    )

    if res.lead is not None and res.reason in LEAD_CAPTURE_IDEMPOTENCY_REASONS:
        _mark_capture_done(collected, res.lead.id)

    if res.created and res.lead is not None:
        if (conversation.channel or "").strip() == CONVERSATION_CHANNEL_TELEGRAM:
            emit_telegram_channel_event(
                telegram_event=TELEGRAM_LEAD_CREATED,
                bot_id=bot.id,
                conversation_id=conversation.id,
                lead_id=res.lead.id,
                creation_reason=res.reason,
            )
        closing = format_lead_capture_closing_message(
            bot_name=bot.name,
            summary_line=summary,
        )
        return SalesPipelineLeadCaptureResult(
            skip_provider=True,
            closing_assistant_text=closing,
            collected_mutated=True,
            created_new_lead=True,
            notify_telegram=True,
            lead_for_telegram=res.lead,
            creation_reason=res.reason,
        )

    return SalesPipelineLeadCaptureResult(
        skip_provider=False,
        closing_assistant_text=None,
        collected_mutated=res.lead is not None and res.reason in LEAD_CAPTURE_DUPLICATE_MERGE_REASONS,
        created_new_lead=False,
        notify_telegram=False,
        lead_for_telegram=None,
        creation_reason=res.reason,
    )


__all__ = [
    "CAPTURED_LEAD_ID_KEY",
    "LEAD_CAPTURE_DONE_KEY",
    "SalesPipelineLeadCaptureResult",
    "format_lead_capture_closing_message",
    "is_lead_capture_marked_done",
    "run_sales_lead_capture_after_pipeline",
]
