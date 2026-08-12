"""
**Lead summary lines** for admins, CRM lists, and Telegram-style alerts.

Strategy (MVP)
==============

**Template-only synthesis** from ``collected_data_json`` plus niche metadata and funnel state.
No LLM: nothing invents adjectives, timelines, or medical/business claims beyond what the user
(or extractor) stored. Optional ``recent_user_messages`` are **verbatim clips** only (last line,
length-capped) so operators can see exact wording without paraphrase risk.

Hybrid later: keep this function as the **fallback** when AI is disabled or confidence is low;
call a small model only when product requires richer copy and you add guardrails.

Safety notes
============

* Every phrase is built from **whitelisted keys** per niche or from **flow core field keys** in
  generic mode — never from free parsing of arbitrary JSON.
* Values are **trimmed and length-clipped**; no enrichment from external data.
* Long paragraphs are avoided via :data:`DEFAULT_MAX_SUMMARY_LENGTH`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence

from app.lib.niche_flow.planner_hooks import field_value_present
from app.lib.niche_flow.registry import get_niche_conversation_flow_or_generic, normalize_niche_flow_id
from app.lib.niche_registry import get_niche_by_id
from app.models.conversation_flow import ConversationFlowState

DEFAULT_MAX_SUMMARY_LENGTH: int = 220
_VERBATIM_USER_MAX: int = 90

_STATE_SNIPPET: dict[str, str] = {
    ConversationFlowState.start.value: "",
    ConversationFlowState.fallback.value: "Needs routing",
    ConversationFlowState.qualification.value: "Qualification",
    ConversationFlowState.clarification.value: "Clarification",
    ConversationFlowState.offer.value: "Offer stage",
    ConversationFlowState.objection_handling.value: "Objection handling",
    ConversationFlowState.closing.value: "Closing",
    ConversationFlowState.completed.value: "Completed",
}


def _txt(data: Mapping[str, object], key: str, *, max_len: int = 96) -> str | None:
    raw = data.get(key)
    if not field_value_present(raw):
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = re.sub(r"\s+", " ", s)
    return s if len(s) <= max_len else s[: max_len - 1].rstrip() + "…"


def _clip(text: str, max_len: int) -> str:
    t = text.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def _summary_education(data: Mapping[str, object]) -> str:
    grade = _txt(data, "student_grade")
    subject = _txt(data, "subject")
    fmt = _txt(data, "lesson_format", max_len=48)
    loc = _txt(data, "branch_or_location", max_len=64)

    modality = ""
    if fmt:
        low = fmt.lower()
        if "online" in low and "in-person" not in low and "on site" not in low:
            modality = "online"
        elif "in-person" in low or "in person" in low or "on-site" in low or "on site" in low:
            modality = "in-person"
        elif "group" in low:
            modality = "group"
        elif re.search(r"1[\s-]*on[\s-]*1|one[\s-]*to[\s-]*one", low):
            modality = "one-to-one"
        else:
            modality = _clip(fmt, 32)

    if subject and grade and modality:
        return f"Parent/learner looking for {modality} {subject} ({grade})."
    if subject and grade:
        return f"Interested in {subject} for {grade}."
    if grade:
        return f"Learner in {grade}."
    if subject:
        return f"Interested in {subject}."
    if modality:
        return f"Prefers {modality} lessons."
    if loc:
        return f"Location preference: {loc}."
    return ""


def _summary_healthcare(data: Mapping[str, object]) -> str:
    specialty = _txt(data, "specialty")
    appt = _txt(data, "appointment_type")
    when = _txt(data, "preferred_time", max_len=64)
    site = _txt(data, "branch_or_location", max_len=64)

    if specialty and appt and when:
        return f"Patient wants {specialty} appointment ({appt}); prefers {when}."
    if specialty and appt:
        return f"Patient wants {specialty} — {appt}."
    if specialty and when:
        return f"Seeking {specialty}; preferred time: {when}."
    if specialty:
        return f"Seeking {specialty} care."
    if appt:
        return f"Appointment type: {appt}."
    if when:
        return f"Preferred scheduling: {when}."
    if site:
        return f"Preferred site/area: {site}."
    return ""


def _summary_dev_agency(data: Mapping[str, object]) -> str:
    solution = _txt(data, "requested_solution", max_len=100)
    channel = _txt(data, "website_or_bot_or_crm", max_len=48)
    budget = _txt(data, "payment_needed", max_len=48)
    scope = _txt(data, "rough_scope", max_len=72)

    if solution and channel:
        base = f"Wants {channel} work: {_clip(solution, 88)}."
    elif solution:
        base = f"Project request: {_clip(solution, 100)}."
    elif channel:
        base = f"Interested in {channel} engagement."
    else:
        base = ""

    extras: list[str] = []
    if budget:
        extras.append(f"budget signal: {budget}")
    if scope:
        extras.append(f"scope: {_clip(scope, 60)}")
    if extras and base:
        return f"{base} ({'; '.join(extras)})."
    if extras:
        return " · ".join(extras) + "."
    return base


def _summary_services(data: Mapping[str, object]) -> str:
    job = _txt(data, "service_type", max_len=72)
    area = _txt(data, "location", max_len=72)
    urg = _txt(data, "urgency", max_len=40)
    avail = _txt(data, "availability", max_len=48)

    if job and area and urg:
        return f"Needs {urg} {job} in/near {area}."
    if job and area:
        return f"Needs {job} in/near {area}."
    if job and urg:
        return f"Needs {urg} {job}."
    if job:
        return f"Service needed: {job}."
    if area:
        return f"Service area: {area}."
    if urg:
        return f"Urgency: {urg}."
    if avail:
        return f"Availability: {avail}."
    return ""


def _summary_generic(niche_id: str, data: Mapping[str, object]) -> str:
    flow = get_niche_conversation_flow_or_generic(niche_id)
    label = get_niche_by_id(flow.niche_id)
    prefix = f"{label.label}: " if label else ""

    parts: list[str] = []
    for spec in flow.core_fields:
        v = _txt(data, spec.key, max_len=56)
        if v:
            parts.append(f"{spec.key.replace('_', ' ')} {v}")

    if not parts:
        return ""

    return prefix + " · ".join(parts) + "."


_NICHE_SUMMARY: dict[str, Callable[[Mapping[str, object]], str]] = {
    "education": _summary_education,
    "healthcare": _summary_healthcare,
    "dev_agency": _summary_dev_agency,
    "services": _summary_services,
}


def generate_lead_summary(
    *,
    niche_id: str,
    collected_data_json: Mapping[str, object] | None,
    conversation_state: str | None = None,
    recent_user_messages: Sequence[str] | None = None,
    max_length: int = DEFAULT_MAX_SUMMARY_LENGTH,
) -> str:
    """
    Build one short admin-facing line. Uses only ``collected_data_json`` values and optional
    verbatim user lines supplied by the caller (e.g. last stored user messages).
    """
    data: Mapping[str, object] = dict(collected_data_json or {})
    key = normalize_niche_flow_id(niche_id)

    fn = _NICHE_SUMMARY.get(key)
    if fn is not None:
        body = fn(data).strip()
    else:
        body = _summary_generic(key or niche_id or "generic", data).strip()

    if not body:
        nd = get_niche_by_id(key or niche_id or "")
        niche_word = nd.label if nd else "Lead"
        body = f"{niche_word}: captured; no qualification fields filled yet."

    state_key = (conversation_state or "").strip().lower()
    st_snip = _STATE_SNIPPET.get(state_key, "")

    segments: list[str] = [body]
    if st_snip:
        segments.append(st_snip)

    if recent_user_messages:
        last = ""
        for raw in reversed(recent_user_messages):
            s = (raw or "").strip()
            if s:
                last = s
                break
        if last:
            clip = _clip(last, _VERBATIM_USER_MAX)
            segments.append(f'Recent: "{clip}"')

    return _clip(" · ".join(segments), max_length)


__all__ = [
    "DEFAULT_MAX_SUMMARY_LENGTH",
    "generate_lead_summary",
]
