"""
**Lead creation from a sales conversation** — gated, deterministic, one row per conversation.

Creation criteria (MVP)
=======================

We only persist a :class:`~app.models.lead.Lead` when **all** of the following hold:

1. **Sales or consulting bot** — ``bot.goal_type in ("sales", "consulting")``. Support/FAQ bots never emit CRM leads here.
2. **Late funnel** — ``conversation.current_state`` is ``closing`` or ``completed``. Offer/clarification
   stages are excluded so we do not spam partial intents before a clear path to handoff.
3. **Required slots complete** — Every niche **required** core field (see
   :func:`~app.lib.niche_flow.planner_hooks.first_missing_required_field_key`) is present in
   ``collected_data_json`` using the same “value present” rules as the question planner.
4. **Phone present** — A callable phone string is required for MVP follow-up: either
   ``explicit_phone`` (when the capture path already normalized it) or any value under the same
   JSON keys as :data:`DEFAULT_LEAD_SCORING_CONFIG.phone_json_keys` inside ``collected_data_json``.

**Why phone is required:** Without a contact channel, a “lead” is usually noise for outbound CRM;
admins can relax this later via config.

**Score / summary** are **inputs**: compute them upstream (e.g. :func:`~app.services.lead_scoring.score_lead`
and :func:`~app.services.lead_summary.generate_lead_summary`) so this service stays a thin persistence gate.

Duplicate prevention & quality
================================

* **Conversation:** Before insert, :meth:`~app.repositories.lead_repository.LeadRepository.get_lead_by_conversation_id`.
* **Open pipeline + same phone:** :mod:`~app.services.lead_safeguards` + repository helpers block a second
  row for the same owner, bot, and normalized phone while an earlier lead is still in ``new`` /
  ``contacted`` / ``qualified`` / ``proposal``.
* **Low-signal payloads:** Same module can skip rows with very low score, almost empty summary, and no name
  (see its docstring — all three must hold). Numeric thresholds are defined only there.
* **Database:** Partial unique index ``uq_leads_conversation_id_not_null`` on ``leads(conversation_id)``
  where ``conversation_id IS NOT NULL`` — second insert races fail with ``IntegrityError``; callers in a
  shared transaction should treat that as “already captured” or run this step after commit in a short
  follow-up transaction.

**Telegram (optional):** Do not call outbound alerts from inside this service. After the surrounding
transaction **commits**, use :class:`~app.services.telegram_lead_alert_service.TelegramLeadAlertService`
(see ``app.integrations.telegram``) so delivery failures never roll back lead creation.

**Ingress:** Eligibility does not depend on ``Conversation.channel``. Widget and Telegram threads both
pass ``source_channel`` through from the conversation row for CRM segmentation only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Literal

from sqlalchemy.exc import IntegrityError

from app.core.logging import get_logger
from app.lib.niche_flow.planner_hooks import field_value_present, first_missing_required_field_key
from app.lib.niche_flow.registry import get_niche_conversation_flow_or_generic, normalize_niche_flow_id
from app.models.conversation_flow import ConversationFlowState
from app.repositories.lead_repository import LeadRepository
from app.services.lead_safeguards import (
    assess_lead_payload_quality,
    normalize_phone_digits,
    phone_correlation_key,
)

# Minimum number of digit characters for a phone to be considered valid.
# Phones with fewer digits are treated as missing (not stored, not used for dedup).
_MIN_PHONE_DIGITS: int = 7
from app.services.lead_scoring import DEFAULT_LEAD_SCORING_CONFIG

if TYPE_CHECKING:
    from app.models.ai_foundation import Conversation
    from app.models.bot import Bot
    from app.models.lead import Lead
    from app.models.user import User
    from app.services.lead_event_service import LeadEventService

_MAX_SUMMARY_CHARS: int = 4000

_LOG = get_logger(__name__)

_ELIGIBLE_FUNNEL_STATES: frozenset[str] = frozenset(
    {
        # The sales engagement flow asks for the phone during the ``offer`` step, so a contactable
        # lead is commonly ready before the machine advances to ``closing``. Capture from ``offer``
        # too — the phone + required-field gates below still apply, so this never over-captures.
        ConversationFlowState.offer.value,
        ConversationFlowState.objection_handling.value,
        ConversationFlowState.closing.value,
        ConversationFlowState.completed.value,
    }
)

LeadCreationReason = Literal[
    "created",
    "skipped_duplicate_conversation",
    "skipped_duplicate_phone_open_pipeline",
    "skipped_low_quality_signals",
    "skipped_not_sales_bot",
    "skipped_funnel_not_ready",
    "skipped_required_fields_incomplete",
    "skipped_phone_required",
    "skipped_owner_bot_conversation_mismatch",
]

# Sales pipeline (:func:`~app.services.sales_lead_capture_turn.run_sales_lead_capture_after_pipeline`)
# uses these sets so capture flags and Telegram gating stay aligned with ``LeadCreationReason``.
LEAD_CAPTURE_IDEMPOTENCY_REASONS: Final[frozenset[str]] = frozenset(
    {
        "created",
        "skipped_duplicate_conversation",
        "skipped_duplicate_phone_open_pipeline",
    }
)
LEAD_CAPTURE_DUPLICATE_MERGE_REASONS: Final[frozenset[str]] = frozenset(
    {
        "skipped_duplicate_conversation",
        "skipped_duplicate_phone_open_pipeline",
    }
)


@dataclass(frozen=True, slots=True)
class LeadCreationResult:
    """Outcome of :meth:`LeadCreationService.try_create_lead_from_conversation`."""

    created: bool
    lead: "Lead | None"
    reason: LeadCreationReason


def _phone_has_enough_digits(phone_str: str) -> bool:
    """Return True when *phone_str* contains at least ``_MIN_PHONE_DIGITS`` digit characters."""
    phone_digits = normalize_phone_digits(phone_str)
    return bool(phone_digits) and len(phone_digits) >= _MIN_PHONE_DIGITS


def extract_phone_for_lead(
    collected_data_json: Mapping[str, object] | None,
    explicit_phone: str | None,
    *,
    json_keys: tuple[str, ...] = DEFAULT_LEAD_SCORING_CONFIG.phone_json_keys,
) -> str | None:
    """
    First valid phone from ``explicit_phone`` or known JSON keys (max 40 chars).

    A phone is considered valid only when it contains at least ``_MIN_PHONE_DIGITS`` (7)
    digit characters after stripping non-digits. Shorter strings (e.g. ``"123"``) are
    treated as missing so they are never stored or used for deduplication.
    """
    if explicit_phone is not None:
        s = str(explicit_phone).strip()
        if s and _phone_has_enough_digits(s):
            return s[:40]
    data = collected_data_json or {}
    for k in json_keys:
        raw = data.get(k)
        if field_value_present(raw):
            s = str(raw).strip()
            if s and _phone_has_enough_digits(s):
                return s[:40]
    return None


def extract_name_from_collected(collected_data_json: Mapping[str, object] | None) -> str | None:
    if not collected_data_json:
        return None
    for k in ("full_name", "name", "contact_name"):
        raw = collected_data_json.get(k)
        if field_value_present(raw):
            return str(raw).strip()[:256]
    return None


def evaluate_lead_creation_gates(
    *,
    bot: "Bot",
    conversation: "Conversation",
    collected_data_json: Mapping[str, object] | None,
    explicit_phone: str | None = None,
    funnel_state_override: str | None = None,
) -> tuple[bool, LeadCreationReason | None]:
    """
    Pure gate check (no I/O). Returns ``(True, None)`` when eligible, else ``(False, skip_reason)``.

    ``funnel_state_override``: when the in-memory funnel position (e.g. post state-machine) differs
    from ``conversation.current_state`` on the ORM row, pass the effective state so gates match the
    planner output (sales orchestrator).
    """
    if bot.goal_type not in ("sales", "consulting"):
        return False, "skipped_not_sales_bot"

    state = (funnel_state_override or conversation.current_state or "").strip().lower()
    if state not in _ELIGIBLE_FUNNEL_STATES:
        return False, "skipped_funnel_not_ready"

    niche_key = normalize_niche_flow_id(
        (conversation.niche_id_snapshot or bot.niche_id or "").strip() or None,
    )
    flow = get_niche_conversation_flow_or_generic(niche_key)
    missing = first_missing_required_field_key(flow, collected_data_json)
    if missing is not None:
        return False, "skipped_required_fields_incomplete"

    if extract_phone_for_lead(collected_data_json, explicit_phone) is None:
        return False, "skipped_phone_required"

    return True, None


def _validate_owner_graph(*, bot: "Bot", owner: "User", conversation: "Conversation") -> bool:
    return (
        bot.owner_id == owner.id
        and conversation.owner_id == owner.id
        and conversation.bot_id == bot.id
    )


def _phone_last4_for_log(digits: str) -> str:
    return digits[-4:] if len(digits) >= 4 else "n/a"


class LeadCreationService:
    """Create :class:`~app.models.lead.Lead` rows when MVP gates pass."""

    def __init__(
        self,
        lead_repo: LeadRepository,
        *,
        events: LeadEventService | None = None,
    ) -> None:
        self._leads = lead_repo
        self._events = events

    async def try_create_lead_from_conversation(
        self,
        *,
        bot: "Bot",
        owner: "User",
        conversation: "Conversation",
        collected_data_json: Mapping[str, object] | None,
        lead_score: int,
        lead_temperature: str,
        summary: str,
        source_channel: str | None,
        explicit_phone: str | None = None,
        funnel_state_override: str | None = None,
    ) -> LeadCreationResult:
        if not _validate_owner_graph(bot=bot, owner=owner, conversation=conversation):
            return LeadCreationResult(
                created=False,
                lead=None,
                reason="skipped_owner_bot_conversation_mismatch",
            )

        eligible, gate_reason = evaluate_lead_creation_gates(
            bot=bot,
            conversation=conversation,
            collected_data_json=collected_data_json,
            explicit_phone=explicit_phone,
            funnel_state_override=funnel_state_override,
        )
        if not eligible:
            return LeadCreationResult(created=False, lead=None, reason=gate_reason or "skipped_not_sales_bot")

        existing = await self._leads.get_lead_by_conversation_id(conversation.id)
        if existing is not None:
            return LeadCreationResult(
                created=False,
                lead=existing,
                reason="skipped_duplicate_conversation",
            )

        niche_id = normalize_niche_flow_id(
            (conversation.niche_id_snapshot or bot.niche_id or "generic").strip(),
        )
        phone = extract_phone_for_lead(collected_data_json, explicit_phone)
        name = extract_name_from_collected(collected_data_json)
        summary_clipped = (summary or "").strip()
        if len(summary_clipped) > _MAX_SUMMARY_CHARS:
            summary_clipped = summary_clipped[: _MAX_SUMMARY_CHARS - 1].rstrip() + "…"

        clamped_score = max(0, min(100, int(lead_score)))
        ok_quality, low_q_reason = assess_lead_payload_quality(
            summary=summary_clipped or "",
            name=name,
            lead_score=clamped_score,
        )
        if not ok_quality and low_q_reason is not None:
            _LOG.warning(
                "lead_creation_safeguard_skip",
                reason=low_q_reason,
                owner_id=str(owner.id),
                bot_id=str(bot.id),
                conversation_id=str(conversation.id),
            )
            return LeadCreationResult(created=False, lead=None, reason=low_q_reason)

        phone_key = phone_correlation_key(phone)
        if phone_key is not None:
            dup_open = await self._leads.find_open_lead_same_normalized_phone(
                owner_id=owner.id,
                bot_id=bot.id,
                phone_digits=phone_key,
            )
            if dup_open is not None:
                _LOG.warning(
                    "lead_creation_safeguard_skip",
                    reason="skipped_duplicate_phone_open_pipeline",
                    owner_id=str(owner.id),
                    bot_id=str(bot.id),
                    conversation_id=str(conversation.id),
                    existing_lead_id=str(dup_open.id),
                    phone_last4=_phone_last4_for_log(phone_key),
                )
                return LeadCreationResult(
                    created=False,
                    lead=dup_open,
                    reason="skipped_duplicate_phone_open_pipeline",
                )

            recent_n = await self._leads.count_leads_same_phone_recent(
                owner_id=owner.id,
                bot_id=bot.id,
                phone_digits=phone_key,
            )
            if recent_n >= 4:
                _LOG.warning(
                    "lead_creation_suspicious_phone_velocity",
                    owner_id=str(owner.id),
                    bot_id=str(bot.id),
                    conversation_id=str(conversation.id),
                    recent_24h_count=recent_n,
                    phone_last4=_phone_last4_for_log(phone_key),
                )

        try:
            # Savepoint so a unique-conversation_id collision from a concurrent turn rolls back
            # only this insert, not the whole turn. Without this the IntegrityError surfaces at
            # commit and fails an otherwise-successful turn even though the lead was captured.
            async with self._leads.session.begin_nested():
                lead = await self._leads.create_lead(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    conversation_id=conversation.id,
                    niche_id=niche_id,
                    lead_score=clamped_score,
                    lead_temperature=lead_temperature,
                    summary=summary_clipped or None,
                    source_channel=(source_channel or "").strip()[:64] or None,
                    collected_data_json=dict(collected_data_json)
                    if collected_data_json is not None
                    else None,
                    phone=phone,
                    name=name,
                )
        except IntegrityError:
            # A concurrent turn won the race and already created the lead for this conversation.
            # Treat as idempotent success rather than failing the turn.
            existing = await self._leads.get_lead_by_conversation_id(conversation.id)
            if existing is not None:
                _LOG.info(
                    "lead_creation_race_resolved_duplicate",
                    owner_id=str(owner.id),
                    bot_id=str(bot.id),
                    conversation_id=str(conversation.id),
                    existing_lead_id=str(existing.id),
                )
                return LeadCreationResult(
                    created=False,
                    lead=existing,
                    reason="skipped_duplicate_conversation",
                )
            raise
        ch = (source_channel or "").strip()[:64] or None
        _LOG.info(
            "lead_created",
            user_id=str(owner.id),
            lead_id=str(lead.id),
            bot_id=str(bot.id),
            conversation_id=str(conversation.id),
            channel=ch,
        )
        if self._events is not None:
            await self._events.emit_lead_created(
                lead_id=lead.id,
                bot_id=bot.id,
                conversation_id=conversation.id,
                source_channel=ch,
                creation_reason="created",
            )
        return LeadCreationResult(created=True, lead=lead, reason="created")


__all__ = [
    "LEAD_CAPTURE_DUPLICATE_MERGE_REASONS",
    "LEAD_CAPTURE_IDEMPOTENCY_REASONS",
    "LeadCreationReason",
    "LeadCreationResult",
    "LeadCreationService",
    "evaluate_lead_creation_gates",
    "extract_phone_for_lead",
    "extract_name_from_collected",
]
