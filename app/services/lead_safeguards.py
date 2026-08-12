"""
MVP **lead quality & duplicate** rules at creation time (deterministic, testable).

Goals
=====

* Cut duplicate CRM noise (same person / same bot while a deal is still open).
* Drop a tiny fraction of obvious junk rows (very low model score + almost no text + no usable name).
* Emit **structured logs** (no full phone numbers) when we skip or see bursty same-phone activity.

Non-goals
=========

* ML-based fraud scoring, rate limiting per IP, or third-party phone reputation.

Rules (thresholds)
==================

**1. Open-pipeline phone duplicate (hard skip)**

* Normalize phone to **digits only** (``0-9``). Empty after normalize → no duplicate check (phone still required upstream).
* If **another lead** exists for the same ``owner_id`` + ``bot_id`` with:

  * the **same** normalized digit string, and
  * ``status`` in ``new``, ``contacted``, ``qualified``, ``proposal``,

  then **do not insert** → ``skipped_duplicate_phone_open_pipeline``.

  *Terminal* rows (``won`` / ``lost``) do **not** block a new capture — a repeat customer can re-enter the funnel.

**2. Low-signal payload (hard skip)**

All must hold to skip as ``skipped_low_quality_signals``:

* ``lead_score < 15``
* stripped ``summary`` length **strictly less than** ``8`` characters (empty counts as 0)
* no **display name** with at least **3** trimmed characters (from collected JSON / explicit name path)

If any condition fails, the lead is allowed — we intentionally avoid blocking borderline real conversations.

**3. Same-phone velocity (soft flag, log only)**

* If **4 or more** leads (any status) exist for the same owner + bot + normalized phone in the **last 24 hours**, log
  ``lead_creation_suspicious_phone_velocity`` at **warning**. Creation still proceeds if other checks passed.

Phone normalization
===================

* Keep only ASCII digits. International formats such as ``+1 (555) 0100`` → ``15550100``.
* If the result has **fewer than 7 digits**, duplicate / velocity queries are **not** applied (too ambiguous; avoids colliding on ``"1"`` test data).

Explainability
==============

Every skip reason is a stable string on :class:`~app.services.lead_creation_service.LeadCreationResult`
for metrics and support.
"""

from __future__ import annotations

import re
from typing import Final

from app.models.lead import LEAD_OPEN_PIPELINE_STATUSES

_DIGITS_ONLY: Final[re.Pattern[str]] = re.compile(r"\D+")

# Do not run phone correlation when fewer than this many digits (avoids false dupes on junk keys).
_MIN_PHONE_DIGITS_FOR_CORRELATION: Final[int] = 7


def normalize_phone_digits(phone: str | None) -> str:
    """Strip to digits only; empty string if missing or no digits."""
    if not phone:
        return ""
    return _DIGITS_ONLY.sub("", str(phone).strip())


def phone_correlation_key(phone: str | None) -> str | None:
    """
    Return normalized digits for DB checks, or ``None`` when too short / empty.

    Short strings are ignored so unit tests and malformed captures do not dedupe everything.
    """
    d = normalize_phone_digits(phone)
    if len(d) < _MIN_PHONE_DIGITS_FOR_CORRELATION:
        return None
    return d


def assess_lead_payload_quality(
    *,
    summary: str,
    name: str | None,
    lead_score: int,
) -> tuple[bool, str | None]:
    """
    Return ``(True, None)`` when the payload may be stored, else ``(False, "skipped_low_quality_signals")``.

    See module docstring for the combined threshold rule.
    """
    s = (summary or "").strip()
    n = (name or "").strip()
    if lead_score >= 15:
        return True, None
    if len(s) >= 8:
        return True, None
    if len(n) >= 3:
        return True, None
    return False, "skipped_low_quality_signals"


OPEN_PIPELINE_STATUSES: Final[tuple[str, ...]] = LEAD_OPEN_PIPELINE_STATUSES

__all__ = [
    "OPEN_PIPELINE_STATUSES",
    "assess_lead_payload_quality",
    "normalize_phone_digits",
    "phone_correlation_key",
]
