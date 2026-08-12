"""
Layer 1 — zero-API input filter for trivial user turns.

Runs **before** Redis, embeddings, intent classifier, or chat completion so greetings and
emoji-only pings cost no tokens and add no vendor latency.

Design contract
---------------
* ``handle_trivial_message`` returns ``None`` for anything that could be a real query.
* Matching is intentionally conservative: only whole-message greeting phrases, emoji-only
  pings, or ultra-short openers whose **every** token is in the trivial lexicon.
* The ``< 3 word`` ceiling is the primary false-positive guard: any message that contains a
  real intent alongside a greeting (e.g. "hi, what is your pricing?") has ≥ 3 words and is
  never trivialised.
* The public API (``handle_trivial_message``, ``trivial_detection_normalized``) is stable;
  do not change signatures without updating callers in ``ai_service.py`` and
  ``sales_conversation_orchestrator.py``.

Structured logs emitted
-----------------------
* ``normalized_inbound_for_trivial`` — DEBUG, every call (trace / diagnostics).
* ``trivial_handled``               — INFO, when the message is classified trivial.
* ``trivial_skipped_nontrivial``    — DEBUG, when the message passes through to the pipeline.
"""

from __future__ import annotations

import re
import unicodedata

from app.core.logging import get_logger

_LOG = get_logger(__name__)


# ---------------------------------------------------------------------------
# Canned responses — brand-safe, human-like, language-appropriate
# ---------------------------------------------------------------------------

_UZ_RESPONSE = "Salom! Qanday yordam bera olaman?"
_RU_RESPONSE = "Привет! Чем могу помочь?"
_EN_RESPONSE = "Hello! How can I help you today?"


# ---------------------------------------------------------------------------
# Greeting phrases — **post-normalisation** whole-message exact match.
#
# Rules for adding entries:
#  • Store the normalised form (lowercase, NFKC, punctuation→space, collapsed).
#  • Phrases with hyphens/apostrophes must be stored without them (e.g. "g day"
#    not "g'day") because normalisation converts those to spaces.
#  • Do NOT add phrases that can prefix a real question (e.g. "hi there how are
#    you" — fine; but "hi how much" would be dangerous without the word-count guard).
# ---------------------------------------------------------------------------

# Uzbek — Latin script
_GREETING_UZ_LATIN: frozenset[str] = frozenset(
    {
        "salom",
        "assalomu alaykum",
        "assalom alaykum",
        "assalamu alaykum",
        "assalam alaykum",
        "as salamu alaykum",      # normalised from "as-salamu alaykum"
        "essalamu alaykum",
        "va alaykum assalom",
        "va alaykum salom",
        "vaalaykum assalom",
    }
)

# Uzbek — Cyrillic script (used by some Uzbek speakers, especially older generation)
_GREETING_UZ_CYRILLIC: frozenset[str] = frozenset(
    {
        "салом",                  # salom in Cyrillic Uzbek
        "ассалому алайкум",
    }
)

# Russian — Cyrillic
_GREETING_RU: frozenset[str] = frozenset(
    {
        "привет",
        "приветствую",
        "здравствуйте",
        "здравствуй",
        "добрый день",
        "добрый вечер",
        "доброе утро",
        "добро пожаловать",
        "хай",
        "хей",
        "дарова",                 # informal Russian greeting
        "приветики",
    }
)

# English
_GREETING_EN: frozenset[str] = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "hay",
        "howdy",
        "hiya",
        "heya",
        "sup",
        "yo",
        "greetings",
        "good morning",
        "good evening",
        "good afternoon",
        "good day",
        "g day",                  # normalised from "g'day"
        "morning",
        "evening",
        "afternoon",
    }
)

# International / other languages
_GREETING_INTL: frozenset[str] = frozenset(
    {
        "namaste",
        "hola",
        "bonjour",
        "ciao",
        "salut",
        "merhaba",
        "shalom",
    }
)

# Full set — union of all language groups
_GREETING_PHRASES: frozenset[str] = (
    _GREETING_UZ_LATIN
    | _GREETING_UZ_CYRILLIC
    | _GREETING_RU
    | _GREETING_EN
    | _GREETING_INTL
)


# ---------------------------------------------------------------------------
# Multi-token trivial lexicon
#
# Used for messages with < 3 words where ALL words must appear in this set.
# The word-count ceiling is the only thing preventing false positives, so be
# conservative: add only words that carry no query intent on their own.
#
# Acknowledgement tokens ("ok", "sure") are included because they have zero
# sales-query signal as standalone 1-word messages.
# ---------------------------------------------------------------------------

_MULTI_TRIVIAL_LEXICON: frozenset[str] = frozenset(
    {
        # --- Uzbek ---
        "salom", "qaleysiz", "qalaysiz", "yaxshimisiz", "qalay", "rahmat",
        "assalomu", "alaykum", "assalom",
        # --- Russian ---
        "привет", "здравствуйте", "здравствуй", "приветствую",
        "хай", "хей", "дарова",
        "добрый", "добрая", "доброе", "день", "вечер", "утро",
        "пока", "давай", "спасибо",
        # --- English greetings ---
        "hi", "hello", "hey", "hay", "howdy", "hiya", "heya",
        "sup", "yo", "greetings", "morning", "evening", "afternoon",
        "good", "dear", "sir", "madam", "there", "you", "team", "a",
        # --- English acknowledgements (zero query-intent as 1-word messages) ---
        "ok", "okay", "k",
        "yes", "no", "yep", "nope",
        "sure", "alright", "fine",
        "cool", "great", "noted",
        "thanks", "thank", "thx", "ty", "np",
        # --- Uzbek yes/no particles ---
        "ha", "yoq",
        # --- International ---
        "hola", "namaste", "bonjour", "ciao", "salut",
    }
)


# ---------------------------------------------------------------------------
# Precompiled patterns for script detection
# ---------------------------------------------------------------------------

_RE_CYRILLIC = re.compile(r"[\u0400-\u04ff]")
_RE_ARABIC = re.compile(r"[\u0600-\u06ff]")
# Match any substring form so "assalomu", "assalamu", "assalom" all hit.
# No word-boundary anchor on the right so suffix variations are covered.
_RE_UZ_WORDS = re.compile(r"(?:salom|assala[mo]\w*|rahmat|qalay|qale|yaxshi)", re.IGNORECASE)
_RE_RU_WORDS = re.compile(
    r"(?:привет|здравствуй|добрый|доброе|спасибо|пожалуйста|пока)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_for_greeting(text: str) -> str:
    """
    Canonical normalisation for greeting detection.

    Steps (order matters):
    1. Strip surrounding whitespace, lowercase.
    2. NFKC Unicode normalisation (decomposes ligatures, normalises dashes, etc.).
    3. Replace any character that is NOT a Unicode word-character or whitespace with
       a single space (removes punctuation, hyphens, apostrophes, brackets …).
    4. Collapse runs of whitespace → single space, strip again.

    The result is suitable for set membership tests against ``_GREETING_PHRASES`` and
    token membership tests against ``_MULTI_TRIVIAL_LEXICON``.
    """
    s = (text or "").strip().lower()
    s = unicodedata.normalize("NFKC", s)
    # \w matches Unicode letters, digits, and _ in all scripts (Python 3 default).
    # Explicit Cyrillic range is redundant but keeps the intent self-documenting.
    s = re.sub(r"[^\w\s\u0400-\u04ff]", " ", s, flags=re.UNICODE)
    return " ".join(s.split())


def _is_emoji_only(text: str) -> bool:
    """
    Return ``True`` when the message contains **no** letters or digits in any script.

    Pure emoji, symbol, or punctuation messages (e.g. "👍", "🎉🙏", "✓") are trivial.
    Any letter (Unicode category L*) or digit (Unicode category N*) makes it non-trivial.
    """
    t = (text or "").strip()
    if not t:
        return False
    for ch in t:
        if ch.isspace():
            continue
        cat = unicodedata.category(ch)
        if cat.startswith("L") or cat.startswith("N"):
            return False
    return True


def _choose_response(bot_language: str | None, original: str) -> str:
    """
    Select the most appropriate canned reply language.

    Priority order:
    1. Explicit ``bot_language`` hint (from bot configuration).
    2. Russian keyword or Cyrillic script in the original message → Russian.
    3. Arabic script or Uzbek-Latin keywords in the original message → Uzbek.
    4. Default → English.
    """
    lang = (bot_language or "").strip().lower()
    if "ru" in lang:
        return _RU_RESPONSE
    if any(x in lang for x in ("uz", "crh", "tg")):
        return _UZ_RESPONSE
    # Script / keyword detection on the raw original (before normalisation)
    if _RE_RU_WORDS.search(original):
        return _RU_RESPONSE
    if _RE_CYRILLIC.search(original):
        return _RU_RESPONSE
    if _RE_ARABIC.search(original):
        return _UZ_RESPONSE
    if _RE_UZ_WORDS.search(original):
        return _UZ_RESPONSE
    return _EN_RESPONSE


def _is_trivial_norm(norm: str, raw: str) -> bool:
    """
    Core classification on an **already normalised** ``norm`` string.

    Returns ``True`` iff the message should be handled by the trivial fast path.
    ``raw`` is only used for the emoji fallback (normalisation strips emoji).
    """
    # Empty raw → not trivial (nothing to respond to)
    if not (raw or "").strip():
        return False

    # Normalisation may strip emoji entirely; handle emoji-only before checking norm
    if not norm:
        return _is_emoji_only(raw)

    # Whole-phrase exact match (covers all multi-word greeting forms)
    if norm in _GREETING_PHRASES:
        return True

    # Token-level check: every word must be in the trivial lexicon, AND
    # the message must be < 3 words (the false-positive guard).
    words = norm.split()
    if len(words) < 3 and all(w in _MULTI_TRIVIAL_LEXICON for w in words):
        return True

    # Emoji-only messages (emoji are stripped by normalisation, norm is empty or short)
    if _is_emoji_only(raw):
        return True

    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def trivial_detection_normalized(text: str) -> str:
    """Normalised form used for greeting / trivial phrase matching (for logs and tests)."""
    return _normalize_for_greeting(text)


def handle_trivial_message(text: str, *, bot_language: str | None = None) -> str | None:
    """
    If the user turn is a pure greeting, emoji-only ping, or ultra-short opener, return
    a fixed human-like reply and **skip** embedding + intent classifier + LLM.

    Returns ``None`` when the message should proceed through the normal pipeline.

    Structured logs emitted:
    * DEBUG ``normalized_inbound_for_trivial`` — always (trace).
    * INFO  ``trivial_handled``                — on match (operational metric).
    * DEBUG ``trivial_skipped_nontrivial``     — on miss (diagnostic).
    """
    raw = (text or "").strip()
    norm = _normalize_for_greeting(raw)

    _LOG.debug(
        "normalized_inbound_for_trivial",
        original_chars=len(raw),
        normalized_chars=len(norm),
        word_count=len(norm.split()) if norm else 0,
    )

    if _is_trivial_norm(norm, raw):
        response = _choose_response(bot_language, raw)
        _LOG.info(
            "trivial_handled",
            normalized_form=norm[:120],
            word_count=len(norm.split()) if norm else 0,
            response_lang="ru" if response is _RU_RESPONSE else ("uz" if response is _UZ_RESPONSE else "en"),
            original_chars=len(raw),
        )
        return response

    _LOG.debug(
        "trivial_skipped_nontrivial",
        normalized_chars=len(norm),
        word_count=len(norm.split()) if norm else 0,
    )
    return None


__all__ = ["handle_trivial_message", "trivial_detection_normalized"]
