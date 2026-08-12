"""
**Deterministic lead scoring** — maps conversation signals to a 0–100 score and a temperature label.

No network calls, no randomness, no opaque ML. Weights live in :class:`LeadScoringConfig` so you can
tune or add per-niche profiles later (see :data:`NICHE_SCORING_CONFIG`).

Scoring logic (MVP)
===================

Points are **additive** and **capped at 100** after summation.

1. **Intent signal** (buying intent vs casual chat) — up to ``max_intent_points``.
   Default map (explicit in config): strongest weight on ``sales_interest`` and ``consulting``,
   lower on ``greeting`` / ``support`` / ``unknown``.

2. **Qualification depth** — up to ``max_qualification_points``, **proportional** to how many
   niche **required** core fields (from :func:`~app.lib.niche_flow.planner_hooks.required_qualification_field_keys`)
   have a present value in ``collected_data_json`` (same “present” rules as the question planner).
   If a niche defines no required fields, **all** core field keys are used for the ratio so generic
   flows still score completeness.

3. **Phone** — ``max_phone_points`` if a phone is passed in or found under a known JSON key
   (``phone_json_keys``), so CRM-ready contactability is rewarded without double-counting free text.

4. **Funnel depth** — up to ``max_funnel_points`` by ``current_state`` (later pipeline stages score
   higher than ``start`` / ``fallback``).

**Temperature** — purely from the final integer score (configurable band maxima):

* **cold** — at or below ``temperature_cold_max``
* **warm** — above cold and at or below ``temperature_warm_max``
* **hot** — above warm max

This keeps labels explainable and aligned with :class:`~app.models.lead.Lead` storage.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final, Literal

from app.lib.niche_flow.planner_hooks import field_value_present, required_qualification_field_keys
from app.lib.niche_flow.registry import get_niche_conversation_flow_or_generic
from app.lib.niche_flow.schema import NicheConversationFlowDefinition
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState

LeadTemperature = Literal["cold", "warm", "hot"]


def _norm_intent(raw: str | None) -> str:
    if raw is None or not str(raw).strip():
        return ConversationDetectedIntent.unknown.value
    key = str(raw).strip().lower().replace("-", "_")
    try:
        return ConversationDetectedIntent(key).value
    except ValueError:
        return ConversationDetectedIntent.unknown.value


def _norm_state(raw: str | None) -> str:
    if raw is None or not str(raw).strip():
        return ConversationFlowState.start.value
    key = str(raw).strip().lower()
    try:
        return ConversationFlowState(key).value
    except ValueError:
        return ConversationFlowState.start.value


@dataclass(frozen=True, slots=True)
class LeadScoreResult:
    """Outcome of :func:`score_lead`."""

    score: int
    """0–100 (clamped), matches ``leads.lead_score`` range."""
    temperature: LeadTemperature
    """Mapped from ``score`` using config band thresholds."""
    breakdown: tuple[tuple[str, int], ...]
    """Human-readable component name and points contributed (before cap)."""


@dataclass(frozen=True, slots=True)
class LeadScoringConfig:
    """
    All weights are **integers**; components sum then clamp to ``max_total_score`` (default 100).

    Adjust these constants when product changes scoring policy — avoid magic numbers in callers.
    """

    max_total_score: int = 100

    max_intent_points: int = 20
    intent_points: Mapping[str, int] = field(
        default_factory=lambda: {
            ConversationDetectedIntent.sales_interest.value: 20,
            ConversationDetectedIntent.consulting.value: 18,
            ConversationDetectedIntent.faq.value: 10,
            ConversationDetectedIntent.greeting.value: 6,
            ConversationDetectedIntent.support.value: 4,
            ConversationDetectedIntent.unknown.value: 0,
        }
    )

    max_qualification_points: int = 45
    max_phone_points: int = 15
    phone_json_keys: tuple[str, ...] = (
        "phone",
        "work_phone",
        "mobile",
        "tel",
        "phone_number",
    )

    max_funnel_points: int = 20
    funnel_state_points: Mapping[str, int] = field(
        default_factory=lambda: {
            ConversationFlowState.start.value: 0,
            ConversationFlowState.fallback.value: 2,
            ConversationFlowState.qualification.value: 8,
            ConversationFlowState.clarification.value: 10,
            ConversationFlowState.offer.value: 14,
            ConversationFlowState.objection_handling.value: 16,
            ConversationFlowState.closing.value: 18,
            ConversationFlowState.completed.value: 20,
        }
    )

    temperature_cold_max: int = 34
    temperature_warm_max: int = 64
    """Scores above this (and ≤ max_total_score) are **hot**."""


DEFAULT_LEAD_SCORING_CONFIG: Final = LeadScoringConfig()

# Future: map niche_id -> LeadScoringConfig() clones with different caps or intent tables.
NICHE_SCORING_CONFIG: dict[str, LeadScoringConfig] = {}


def _config_for_niche(niche_id: str) -> LeadScoringConfig:
    key = (niche_id or "").strip().lower().replace("-", "_")
    return NICHE_SCORING_CONFIG.get(key, DEFAULT_LEAD_SCORING_CONFIG)


def _qualification_depth_points(
    flow: NicheConversationFlowDefinition,
    collected: Mapping[str, object] | None,
    max_points: int,
) -> tuple[int, str]:
    data = collected or {}
    required = required_qualification_field_keys(flow)
    keys = required if required else tuple(f.key for f in flow.core_fields)
    if not keys or max_points <= 0:
        return 0, "qualification_depth"
    filled = sum(1 for k in keys if field_value_present(data.get(k)))
    # Integer math — deterministic, no floats.
    points = (filled * max_points) // len(keys)
    return points, "qualification_depth"


def _phone_signal(
    phone: str | None,
    collected: Mapping[str, object] | None,
    json_keys: tuple[str, ...],
    max_points: int,
) -> tuple[int, str]:
    if max_points <= 0:
        return 0, "phone"
    data = collected or {}
    if phone is not None and str(phone).strip():
        return max_points, "phone"
    for k in json_keys:
        if field_value_present(data.get(k)):
            return max_points, "phone"
    return 0, "phone"


def score_lead(
    *,
    niche_id: str,
    detected_intent: str | None,
    collected_data_json: Mapping[str, object] | None,
    phone: str | None = None,
    conversation_state: str | None = None,
    config: LeadScoringConfig | None = None,
) -> LeadScoreResult:
    """
    Compute score and temperature from conversation snapshot fields.

    ``conversation_state`` should be the persisted sales funnel state (e.g. ``conversations.current_state``).
    """
    cfg = config or _config_for_niche(niche_id)
    flow = get_niche_conversation_flow_or_generic(niche_id)

    intent_key = _norm_intent(detected_intent)
    intent_pts = min(cfg.max_intent_points, int(cfg.intent_points.get(intent_key, 0)))

    qual_pts, _ = _qualification_depth_points(flow, collected_data_json, cfg.max_qualification_points)

    phone_pts, _ = _phone_signal(phone, collected_data_json, cfg.phone_json_keys, cfg.max_phone_points)

    state_key = _norm_state(conversation_state)
    funnel_pts = min(cfg.max_funnel_points, int(cfg.funnel_state_points.get(state_key, 0)))

    raw_total = intent_pts + qual_pts + phone_pts + funnel_pts
    total = max(0, min(cfg.max_total_score, raw_total))

    cold_max = cfg.temperature_cold_max
    warm_max = cfg.temperature_warm_max
    if total <= cold_max:
        temp: LeadTemperature = "cold"
    elif total <= warm_max:
        temp = "warm"
    else:
        temp = "hot"

    breakdown = (
        ("intent", intent_pts),
        ("qualification_depth", qual_pts),
        ("phone", phone_pts),
        ("funnel_depth", funnel_pts),
    )
    return LeadScoreResult(score=total, temperature=temp, breakdown=breakdown)


__all__ = [
    "DEFAULT_LEAD_SCORING_CONFIG",
    "LeadScoreResult",
    "LeadScoringConfig",
    "LeadTemperature",
    "NICHE_SCORING_CONFIG",
    "score_lead",
]
