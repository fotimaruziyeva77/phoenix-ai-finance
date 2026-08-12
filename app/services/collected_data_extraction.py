"""
**Collected-data extraction** — map user replies into ``collected_data_json`` keys.

MVP approach: **rule-based + targeted field** (from question planner). This is stable,
testable, and cheap. Optional **AI-assisted** extraction can wrap the same merge API later
by supplying additional ``proposed`` keys with confidence gating.

**Design**
    * :func:`propose_extractions_from_user_message` returns *candidates* only; it never
      decides overwrite policy.
    * :func:`merge_collected_data` performs **safe merge**: by default fills **empty** slots
      only, preserving existing non-empty values so we do not clobber good data.
    * :func:`apply_user_reply_to_collected_data` runs propose → merge and reports which
      keys changed (audit trail).
    * Heuristics are intentionally shallow; unknown text for the active slot may fall back to
      **trimmed verbatim** when gated by ``_generic_verbatim_ok`` / ``_student_grade_verbatim_ok``
      (aligned in spirit with :mod:`app.services.sales_safeguards` vague detection).
    * Pass ``target_field_key`` from the question planner (or equivalent) each turn; without
      it, :func:`propose_extractions_from_user_message` returns nothing so we do not guess
      which slot the user answered.

**Future**
    * Pydantic validators per niche or JSON Schema for ``collected_data_json``.
    * ``keys_allow_overwrite`` / confidence scores from an LLM extractor.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from app.lib.niche_flow.planner_hooks import field_value_present
from app.lib.niche_flow.schema import NicheConversationFlowDefinition

_MAX_VERBATIM_CHARS: int = 400

# Word-ish tokens (aligned with sales safeguards) — used to avoid storing punctuation / filler as slot values.
_WORDISH_TOKEN_RE = re.compile(r"[0-9A-Za-z\u0400-\u04FF]{2,}")

# Single-token replies that plausibly mean a grade / level without digits (verbatim into student_grade).
_STUDENT_GRADE_SINGLE_WORD_OK = re.compile(
    r"(?i)^(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"kindergarten|preschool|homeschooled?|undergraduate|postgraduate)$"
)

_STUDENT_GRADE_VERBATIM_HINT = re.compile(
    r"(?i)\d|"
    r"\b(grade|grader|gr\.?|year|kindergarten|kg|student|learner|adult|child|kids?|"
    r"school|homesch|middle|high|elementary|college|university|sophomore|junior|senior|"
    r"freshman|toddler|teen|primary|secondary)\b"
)

# Phone-like candidate: an optional leading "+", then digits possibly separated by spaces,
# dashes, parentheses or dots. Validated afterwards by digit count + a "looks like a phone"
# heuristic so bare numbers (order ids, quantities) are not mistaken for contact numbers.
_PHONE_CANDIDATE_RE = re.compile(r"\+?\d[\d\s().\-]{5,}\d")
# Minimum digits for a callable phone (mirrors app.services.lead_creation_service._MIN_PHONE_DIGITS).
_PHONE_MIN_DIGITS = 7


def _extract_phone(text: str) -> str | None:
    """
    Best-effort phone detection from free text (any language).

    A candidate counts as a phone when it has at least ``_PHONE_MIN_DIGITS`` digits AND either
    starts with ``+``, contains a separator (space/dash/paren/dot), or has 9+ digits. This keeps
    real numbers like ``+998 88 378 08 08`` / ``901234567`` while ignoring short quantities and
    bare ids embedded in the reply.
    """
    for match in _PHONE_CANDIDATE_RE.finditer(text or ""):
        candidate = match.group(0).strip()
        digits = re.sub(r"\D", "", candidate)
        if len(digits) < _PHONE_MIN_DIGITS:
            continue
        has_separator = bool(re.search(r"[+\s().\-]", candidate))
        if candidate.startswith("+") or len(digits) >= 9 or has_separator:
            return candidate[:40]
    return None


def _wordish_token_count(text: str) -> int:
    return len(_WORDISH_TOKEN_RE.findall(text.strip()))


def _generic_verbatim_ok(text: str) -> bool:
    """
    Free-text slots should not capture obvious non-answers (``?``, ``ok``) but may capture short
    real values (e.g. ``Math``, ``Denver``).
    """
    s = text.strip()
    wc = _wordish_token_count(s)
    return wc >= 2 or (wc == 1 and len(s) >= 4)


def _student_grade_verbatim_ok(text: str) -> bool:
    """Avoid verbatim junk (``?``, random words) into ``student_grade`` while keeping real short answers."""
    s = text.strip()
    if not s:
        return False
    if _STUDENT_GRADE_VERBATIM_HINT.search(s):
        return True
    if _STUDENT_GRADE_SINGLE_WORD_OK.match(s):
        return True
    wc = _wordish_token_count(s)
    if wc == 1 and len(s) >= 10:
        return True
    return False


@dataclass(frozen=True, slots=True)
class CollectedDataMergeOutcome:
    """Result of propose + merge; safe to log for audits."""

    collected_data: dict[str, object]
    proposed_extractions: dict[str, object]
    keys_written: tuple[str, ...]
    """Keys whose value changed compared to ``existing`` (shallow compare)."""
    audit_trail: tuple[str, ...]


def allowed_core_field_keys(flow: NicheConversationFlowDefinition) -> frozenset[str]:
    """Keys the extractor may write (niche ``core_fields`` only)."""
    return frozenset(f.key for f in flow.core_fields)


def merge_collected_data(
    existing: Mapping[str, object] | None,
    proposed: Mapping[str, object] | None,
    *,
    allowed_keys: frozenset[str],
    only_if_empty: bool = True,
    keys_allow_overwrite: frozenset[str] | None = None,
) -> dict[str, object]:
    """
    Shallow merge into a new dict. Unknown keys are dropped unless in ``allowed_keys``.

    * ``only_if_empty`` — do not replace a slot that :func:`field_value_present` considers filled.
    * ``keys_allow_overwrite`` — optional escape hatch for corrections (future).
    """
    out: dict[str, object] = dict(existing or {})
    overwrite_ok = keys_allow_overwrite or frozenset()
    prop = proposed or {}
    for key, raw in prop.items():
        if key not in allowed_keys:
            continue
        if not field_value_present(raw):
            continue
        normalized = _normalize_value(raw)
        if normalized is None:
            continue
        if only_if_empty and key not in overwrite_ok and field_value_present(out.get(key)):
            continue
        out[key] = normalized
    return out


def _normalize_value(raw: object) -> object | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        s = raw.strip()
        return s if s else None
    if isinstance(raw, (bool, int, float)):
        return raw
    if isinstance(raw, (list, dict)):
        return raw if raw else None
    return str(raw).strip() or None


def _audit(msg: str) -> str:
    return msg


def _verbatim_or_none(text: str) -> str | None:
    s = text.strip()
    if not s or len(s) > _MAX_VERBATIM_CHARS:
        return None
    return s


# --- Light heuristics (conservative) ---


def _extract_student_grade(text: str) -> str | None:
    t = text.lower()
    if re.search(r"\bkindergarten\b|\bkg\b", t):
        return "Kindergarten"
    m = re.search(r"\b(?:grade|gr\.?)\s*(\d{1,2})\b", t)
    if m:
        return f"Grade {int(m.group(1))}"
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+grade\b", t)
    if m:
        return f"Grade {int(m.group(1))}"
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)\s+grader\b", t)
    if m:
        return f"Grade {int(m.group(1))}"
    m = re.search(r"\byear\s*(\d{1,2})\b", t)
    if m:
        return f"Year {int(m.group(1))}"
    return None


def _extract_lesson_format(text: str) -> str | None:
    t = text.lower()
    if re.search(r"\bhybrid\b", t):
        return "hybrid"
    if re.search(r"\bonline\b|\bremote\b|\bvirtual\b", t) and not re.search(
        r"\bin[\s-]?person\b|\bon[\s-]?site\b",
        t,
    ):
        return "online"
    if re.search(r"\bin[\s-]?person\b|\bon[\s-]?site\b|\bat\s+the\s+(branch|center|campus)\b", t):
        return "in-person"
    if re.search(r"\bone[\s-]?to[\s-]?one\b|\b1[\s-]?on[\s-]?1\b|\btutoring\b", t):
        return "one-to-one"
    if re.search(r"\bgroup\b", t):
        return "group"
    return None


def _extract_appointment_type(text: str) -> str | None:
    t = text.lower()
    if re.search(r"\bfirst\b.*\bvisit\b|\bnew\s+patient\b|\binitial\b", t):
        return "first visit"
    if re.search(r"\bfollow[\s-]?up\b|\breturning\b", t):
        return "follow-up"
    if re.search(r"\bcleaning\b|\bcheck[\s-]?up\b|\bcheckup\b", t):
        return "routine visit"
    return None


def _extract_channel_build(text: str) -> str | None:
    t = text.lower()
    if re.search(r"\bchatbot\b|\bchat\s+bot\b", t):
        return "chatbot"
    # CRM before generic "integration" substring (e.g. "CRM integration").
    if re.search(r"\bcrm\b", t):
        return "CRM"
    if re.search(r"\bwebsite\b|\bweb\s+site\b|\blanding\b", t):
        return "website"
    if re.search(r"\bmobile\s+app\b|\bios\b|\bandroid\b", t):
        return "mobile app"
    if re.search(r"\bintegrat\b|\bapi\b", t):
        return "integration/API"
    return None


def _extract_urgency(text: str) -> str | None:
    t = text.lower()
    if re.search(r"\bemergency\b|\burgent\b|\bright\s+now\b|\btoday\b|\bimmediately\b", t):
        return "urgent"
    if re.search(r"\bthis\s+week\b|\basap\b", t):
        return "this week"
    if re.search(r"\bflexible\b|\bwhenever\b|\bno\s+rush\b", t):
        return "flexible"
    return None


def _specialized_value(field_key: str, text: str) -> str | None:
    if field_key == "student_grade":
        return _extract_student_grade(text)
    if field_key == "lesson_format":
        return _extract_lesson_format(text)
    if field_key == "appointment_type":
        return _extract_appointment_type(text)
    if field_key == "website_or_bot_or_crm":
        return _extract_channel_build(text)
    if field_key == "urgency":
        return _extract_urgency(text)
    return None


def propose_extractions_from_user_message(
    user_message: str,
    niche_flow: NicheConversationFlowDefinition,
    *,
    target_field_key: str | None = None,
) -> tuple[dict[str, object], tuple[str, ...]]:
    """
    Propose field updates from a single user turn.

    When ``target_field_key`` is set and matches a core field, we try a specialized
    extractor first, then fall back to trimmed verbatim text.
    """
    allowed = allowed_core_field_keys(niche_flow)
    text = (user_message or "").strip()
    if not text:
        return {}, ()

    proposals: dict[str, object] = {}
    audit: list[str] = []

    if target_field_key and target_field_key in allowed:
        spec = _specialized_value(target_field_key, text)
        if spec is not None:
            proposals[target_field_key] = spec
            audit.append(_audit(f"rule:{target_field_key}:specialized"))
        else:
            vb = _verbatim_or_none(text)
            if vb is None:
                pass
            elif target_field_key == "student_grade":
                if _student_grade_verbatim_ok(text):
                    proposals[target_field_key] = vb
                    audit.append(_audit(f"rule:{target_field_key}:verbatim"))
            elif _generic_verbatim_ok(text):
                proposals[target_field_key] = vb
                audit.append(_audit(f"rule:{target_field_key}:verbatim"))

    return proposals, tuple(audit)


def apply_user_reply_to_collected_data(
    existing: Mapping[str, object] | None,
    user_message: str,
    niche_flow: NicheConversationFlowDefinition,
    *,
    target_field_key: str | None = None,
    only_if_empty: bool = True,
    keys_allow_overwrite: frozenset[str] | None = None,
) -> CollectedDataMergeOutcome:
    """Propose extractions from ``user_message`` and merge into a copy of ``existing``."""
    proposed, trail_propose = propose_extractions_from_user_message(
        user_message,
        niche_flow,
        target_field_key=target_field_key,
    )
    allowed = allowed_core_field_keys(niche_flow)
    merged = merge_collected_data(
        existing,
        proposed,
        allowed_keys=allowed,
        only_if_empty=only_if_empty,
        keys_allow_overwrite=keys_allow_overwrite,
    )
    prior = dict(existing or {})
    keys_written_list: list[str] = []
    for k in proposed:
        if k not in allowed or k not in merged:
            continue
        if prior.get(k) != merged.get(k):
            keys_written_list.append(k)

    # Universal contact capture: a phone is not a niche core field, so the core-field merge
    # above never stores it. Detect it from the raw reply and write it under the standard
    # ``phone`` key (one of ``DEFAULT_LEAD_SCORING_CONFIG.phone_json_keys``) so lead capture
    # can find it. Only fill when empty — never clobber a previously captured number.
    if not field_value_present(merged.get("phone")):
        phone = _extract_phone(user_message)
        if phone is not None:
            merged["phone"] = phone
            keys_written_list.append("phone")

    keys_written = tuple(keys_written_list)
    full_audit = trail_propose + tuple(f"merge:keys_considered={sorted(proposed.keys())}")
    return CollectedDataMergeOutcome(
        collected_data=merged,
        proposed_extractions=dict(proposed),
        keys_written=keys_written,
        audit_trail=full_audit,
    )


__all__ = [
    "CollectedDataMergeOutcome",
    "allowed_core_field_keys",
    "apply_user_reply_to_collected_data",
    "merge_collected_data",
    "propose_extractions_from_user_message",
]
