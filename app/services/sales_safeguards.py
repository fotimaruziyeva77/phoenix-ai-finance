"""
Sales conversation **safeguards** — abuse, confusion, and loop control before/after extraction.

**Design goals**
    * Do not frustrate normal users (high thresholds, recovery-friendly copy).
    * Never surface stack traces or internal codes to end users.
    * Avoid infinite loops: every branch returns a canned nudge and resets streak counters while keeping
      the funnel in **qualification** so the same slot target remains (user can answer clearly next turn).

**Threshold rationale** (tunable via constants below)

* **Hard length (12k chars)** — far above a typical qualification reply; catches paste spam and prompt
  injection dumps while allowing long pastes from genuine users (they get a polite ask to shorten).
* **Soft rate (24 turns / 60s)** — very high for human typing; blocks scripted floods without hitting
  rapid legitimate correction bursts.
* **Identical short message streak (5)** — same text under 96 chars repeated five times is almost
  never a confused human; normal “yes” confirmations differ by turn context.
* **Missed slot streak (4)** — same ``__orch_target_field`` four turns with no extracted value
  suggests the model question or user input is stuck; we nudge clarification and reset the streak.
* **Vague streak (4)** — tiny or punctuation-only replies while a slot is targeted; after four,
  we ask for a clearer answer via clarification.
* **Weak Gemini confidence (<0.48)** — between the classifier floor (0.42) and “comfortable” band;
  model-sourced intents below this are routed as ``unknown`` so the funnel can use fallback/recovery
  instead of over-committing to a shaky label.

Internal keys (prefixed ``_sf_``) live in ``collected_data_json`` and are filtered from admin “captured
fields” previews on the frontend.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Final

from app.models.conversation_flow import ConversationDetectedIntent
from app.services.intent_types import IntentClassificationResult

# --- Length ---
# 12k: extreme paste / abuse; normal replies rarely exceed a few hundred characters.
SALES_USER_HARD_MAX_CHARS: Final = 12_000

# --- Rate (sliding window, per conversation, stored in collected_data_json) ---
SALES_RATE_WINDOW_SEC: Final = 60.0
# 24 messages/minute sustained is far beyond human conversation; allows fast testing without hitting normal use.
SALES_RATE_MAX_TURNS_IN_WINDOW: Final = 24

# --- Repeated identical input (normalized) ---
SALES_IDENTICAL_STREAK_MAX: Final = 5
SALES_IDENTICAL_MAX_NORMALIZED_LEN: Final = 96

# --- Same targeted slot missed repeatedly ---
SALES_SAME_TARGET_MISS_STREAK_MAX: Final = 4

# --- Vague reply while a slot is expected ---
SALES_VAGUE_STREAK_MAX: Final = 4
# Fewer than this many “word-like” tokens counts as vague when a field is targeted.
SALES_VAGUE_MIN_WORDISH_TOKENS: Final = 2

# --- Weak model intent (routing only) ---
SALES_WEAK_GEMINI_CONFIDENCE: Final = 0.48

_KEY_TURN_TS: Final = "_sf_turn_ts"
_KEY_IDENT_LAST: Final = "_sf_ident_last"
_KEY_IDENT_STREAK: Final = "_sf_ident_streak"
_KEY_MISS_STREAK: Final = "_sf_miss_streak"
_KEY_MISS_FIELD: Final = "_sf_miss_field"
_KEY_VAGUE_STREAK: Final = "_sf_vague_streak"


def _normalize_user_text(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def _wordish_token_count(text: str) -> int:
    """Rough count of letter/digit runs — filters pure punctuation / emoji spam."""
    return len(re.findall(r"[0-9A-Za-z\u0400-\u04FF]{2,}", text))


@dataclass(frozen=True, slots=True)
class SafeguardDecision:
    """If ``block_llm`` is True, orchestrator must not call the chat model this turn."""

    block_llm: bool
    canned_user_message: str | None
    reason_code: str
    """Stable analytics code, not shown to users."""


def _prune_turn_timestamps(raw: object, *, now: float) -> list[float]:
    if not isinstance(raw, list):
        return []
    out: list[float] = []
    for x in raw[-40:]:
        try:
            t = float(x)
        except (TypeError, ValueError):
            continue
        if now - t <= SALES_RATE_WINDOW_SEC:
            out.append(t)
    return out


def evaluate_early_turn_guards(
    text: str,
    collected: dict[str, object],
    *,
    now: float | None = None,
) -> SafeguardDecision | None:
    """
    Run **before** intent classification. Mutates ``collected`` for rolling counters (rate, identical streak).

    Returns a :class:`SafeguardDecision` to short-circuit with a canned reply, or ``None`` to continue.
    """
    tnow = time.time() if now is None else float(now)

    ts = _prune_turn_timestamps(collected.get(_KEY_TURN_TS), now=tnow)
    ts.append(tnow)
    collected[_KEY_TURN_TS] = ts
    if len(ts) > SALES_RATE_MAX_TURNS_IN_WINDOW:
        return SafeguardDecision(
            block_llm=True,
            canned_user_message=(
                "You’re sending messages very quickly. Pause for a moment, then send your question "
                "when you’re ready — I’ll be right here."
            ),
            reason_code="safeguard_rate_limit",
        )

    norm = _normalize_user_text(text)
    if len(norm) <= SALES_IDENTICAL_MAX_NORMALIZED_LEN and norm:
        last = collected.get(_KEY_IDENT_LAST)
        last_s = str(last).strip() if last is not None else ""
        streak = int(collected.get(_KEY_IDENT_STREAK, 0) or 0)
        if norm == last_s:
            streak = streak + 1
        else:
            streak = 1
        collected[_KEY_IDENT_LAST] = norm
        collected[_KEY_IDENT_STREAK] = streak
        if streak >= SALES_IDENTICAL_STREAK_MAX:
            return SafeguardDecision(
                block_llm=True,
                canned_user_message=(
                    "I’m having trouble understanding that. In your own words, what would you like help with today?"
                ),
                reason_code="safeguard_identical_spam",
            )
    elif norm:
        collected[_KEY_IDENT_STREAK] = 1
        collected[_KEY_IDENT_LAST] = norm

    if len(text) > SALES_USER_HARD_MAX_CHARS:
        return SafeguardDecision(
            block_llm=True,
            canned_user_message=(
                "Thanks for writing in — that message is longer than I can take in here. "
                "Could you share the main thing you’re looking for in a short paragraph?"
            ),
            reason_code="safeguard_message_too_long",
        )

    return None


def effective_routing_intent(ic: IntentClassificationResult) -> ConversationDetectedIntent:
    """
    Downgrade shaky **Gemini** classifications to ``unknown`` so the state machine can use fallback/recovery.

    Rule-based intents are left unchanged (they already use high-precision patterns).
    """
    if ic.source != "gemini":
        return ic.intent
    if ic.confidence >= SALES_WEAK_GEMINI_CONFIDENCE:
        return ic.intent
    return ConversationDetectedIntent.unknown


def evaluate_post_extraction_guards(
    text: str,
    *,
    extraction_target: str | None,
    keys_written: tuple[str, ...],
    collected: dict[str, object],
) -> SafeguardDecision | None:
    """
    After slot extraction. May return a canned reply without LLM (stays in qualification; slot target unchanged).

    Mutates ``collected`` for streak counters.
    """
    mutations: dict[str, object] = {}

    if keys_written:
        mutations[_KEY_MISS_STREAK] = 0
        mutations[_KEY_MISS_FIELD] = ""
        mutations[_KEY_VAGUE_STREAK] = 0
        collected.update(mutations)
        return None

    target = (extraction_target or "").strip() or None

    # Vague reply detection (only when we expected a substantive answer for a slot)
    if target:
        wc = _wordish_token_count(text)
        vague_streak = int(collected.get(_KEY_VAGUE_STREAK, 0) or 0)
        if wc < SALES_VAGUE_MIN_WORDISH_TOKENS:
            vague_streak += 1
        else:
            vague_streak = 0
        mutations[_KEY_VAGUE_STREAK] = vague_streak

        miss_streak = int(collected.get(_KEY_MISS_STREAK, 0) or 0)
        last_field = str(collected.get(_KEY_MISS_FIELD, "") or "")
        if target == last_field:
            miss_streak += 1
        else:
            miss_streak = 1
        mutations[_KEY_MISS_STREAK] = miss_streak
        mutations[_KEY_MISS_FIELD] = target

        collected.update(mutations)

        if vague_streak >= SALES_VAGUE_STREAK_MAX:
            return SafeguardDecision(
                block_llm=True,
                canned_user_message=(
                    "I didn’t quite catch that — could you add a little more detail so I can help you properly?"
                ),
                reason_code="safeguard_vague_repeated",
            )

        if miss_streak >= SALES_SAME_TARGET_MISS_STREAK_MAX:
            collected[_KEY_MISS_STREAK] = 0
            collected.pop(_KEY_MISS_FIELD, None)
            return SafeguardDecision(
                block_llm=True,
                canned_user_message=(
                    "Let’s take a quick step back — what’s the single most important thing you need from us right now?"
                ),
                reason_code="safeguard_same_slot_loop",
            )

    return None


__all__ = [
    "SALES_IDENTICAL_MAX_NORMALIZED_LEN",
    "SALES_IDENTICAL_STREAK_MAX",
    "SALES_RATE_MAX_TURNS_IN_WINDOW",
    "SALES_RATE_WINDOW_SEC",
    "SALES_SAME_TARGET_MISS_STREAK_MAX",
    "SALES_USER_HARD_MAX_CHARS",
    "SALES_VAGUE_MIN_WORDISH_TOKENS",
    "SALES_VAGUE_STREAK_MAX",
    "SALES_WEAK_GEMINI_CONFIDENCE",
    "SafeguardDecision",
    "effective_routing_intent",
    "evaluate_early_turn_guards",
    "evaluate_post_extraction_guards",
]
