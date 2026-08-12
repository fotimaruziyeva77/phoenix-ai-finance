"""
High-confidence, deterministic intent hints (MVP).

Returns ``None`` when the message should be classified by the model instead.
Designed for niche-specific extensions later via optional ``niche_hint`` hooks.

Includes lightweight **Uzbek (Latin)** cues for common education / healthcare / commerce /
home-service requests so local phrasing classifies without an extra model call when obvious.
"""

from __future__ import annotations

import re

from app.models.conversation_flow import ConversationDetectedIntent

# Short salutations only — avoid classifying “hi, I need a refund” as pure greeting.
_GREETING_ONLY = re.compile(
    r"^("
    r"hi(\s+there)?|hello(\s+there)?|hey(\s+there)?|howdy|greetings|"
    r"good\s+(morning|afternoon|evening|day)|hola|bonjour"
    r")[\s!?.…]*$",
    re.IGNORECASE,
)

_SUPPORT_MARKERS = re.compile(
    r"\b("
    r"help\b|support|doesn'?t\s+work|not\s+working|broken|error|bug|issue|problem|"
    r"fix|refund|complaint|ticket|crash|failed|failure"
    r")\b",
    re.IGNORECASE,
)

_SALES_MARKERS = re.compile(
    r"\b("
    r"buy|purchase|order|pricing|price|quote|demo|trial|signup|sign\s*up|subscribe|"
    r"package|plan|discount|cost\b|how\s+much"
    r")\b",
    re.IGNORECASE,
)

_CONSULTING_MARKERS = re.compile(
    r"\b("
    r"consult|consulting|strategy|audit|roadmap|advis(e|or)|workshop|retainer|"
    r"professional\s+services"
    r")\b",
    re.IGNORECASE,
)

_FAQ_MARKERS = re.compile(
    r"\b("
    r"what\s+is|what\s+are|how\s+do\s+i|how\s+to|where\s+(is|do|can)|"
    r"when\s+(is|do|can)|why\s+(is|do|can)|policy|hours|location|shipping|warranty"
    r")\b",
    re.IGNORECASE,
)

# Availability inquiry — "do you have X", "is X in stock", "available?"
_AVAILABILITY_MARKERS = re.compile(
    r"\b("
    r"available|availability|in[\s\-]stock|out[\s\-]of[\s\-]stock|"
    r"do\s+you\s+(have|offer|sell|provide|carry)|"
    r"is\s+(it|that|this)\s+available|stock"
    r")\b",
    re.IGNORECASE,
)

# Contact request — asking for a phone, email, WhatsApp, or how to reach the business
_CONTACT_MARKERS = re.compile(
    r"\b("
    r"contact(\s+us|\s+you)?|call\s+me|call\s+us|reach\s+out|get\s+in\s+touch|"
    r"phone\s*(number|no\.?)?|whatsapp|telegram\s*(number|no\.?)?|"
    r"email\s*(address|me|us)?|your\s+(number|email|phone)|"
    r"how\s+(do\s+i|can\s+i|to)\s+contact|send\s+me\s+your"
    r")\b",
    re.IGNORECASE,
)

# Booking / speak-with-human intent — appointments, scheduling, requesting an agent
_BOOKING_MARKERS = re.compile(
    r"\b("
    r"book|booking|appointment|schedule\b|"
    r"speak\s+with|talk\s+to\s+(an?|the|your|a\s+person|someone)|"
    r"meet\s+with|connect\s+me|talk\s+to\s+agent|"
    r"live\s+agent|human\s+agent|real\s+person|speak\s+to\s+(a\s+)?person|"
    r"manager|admin\b"
    r")\b",
    re.IGNORECASE,
)

# Uzbek (Latin) + common regional cues: “I need …” service/course/commerce requests.
# Long windows tolerate agglutination (e.g. farzandim … kursi kerak).
_UZ_GREETING = re.compile(
    r"^(assalomu\s+alaykum|salom|qalaysiz|qandaysiz)[\s!?.…]*$",
    re.IGNORECASE,
)

_UZ_EDUCATION_NEED = re.compile(
    r"(farzand|o'?quvchi|matematika|algebra|geometriya|ingliz\s*tili|kurs).{0,120}\bkerak\b|"
    r"\bkerak\b.{0,120}(matematika|kurs|o'?qit|ta'lim)",
    re.IGNORECASE,
)

_UZ_HEALTHCARE_BOOKING = re.compile(
    r"stomatolog|tish\s*shifokori|shifokor|klinika|"
    r"qabul|yozilmoqchi|navbat|tekshiruv|operatsiya",
    re.IGNORECASE,
)

_UZ_DIGITAL_COMMERCE = re.compile(
    r"online\s*magazin|onlayn\s*magazin|internet\s*magazin|"
    r"veb[\s-]?sayt|sayt\s*yas|sayt\s*kerak|internet[\s-]?do['\u2019]?kon|e[\s-]?commerce",
    re.IGNORECASE,
)

_UZ_HOME_TRADES = re.compile(
    r"uy(im)?ga\s+usta|uyga\s+usta|\busta\b.{0,24}\bkerak\b|\bkerak\b.{0,24}\busta\b|"
    r"\bremont\b|\bsantexnik\b|\belektrik\b",
    re.IGNORECASE,
)

# Minimal acknowledgments in a sales funnel — classify as sales_interest so the state machine
# keeps a "known" intent (unknown would force fallback during qualification).
_SHORT_ACK_ONLY = re.compile(
    r"^("
    r"ok|okay|k|ya|yep|yeah|yes|no|nope|nah|sure|thanks?|thx|ty|cool|great|nice|got\s*it|understood|alright|fine"
    r")[\s!?.…]*$",
    re.IGNORECASE,
)


def classify_by_rules(
    message: str,
    *,
    niche_hint: str | None = None,
) -> tuple[ConversationDetectedIntent, float] | None:
    """
    If patterns match with high confidence, return ``(intent, confidence)``.

    ``niche_hint`` is reserved for future routing (e.g. niche-specific keyword lists);
    it does not affect MVP matching.

    Returns ``None`` to defer to the AI classifier.
    """
    _ = niche_hint  # Sprint 8+: optional niche keyword tables
    text = (message or "").strip()
    if not text:
        return None

    # Greeting: short, greeting-only lines.
    if len(text) <= 56 and _GREETING_ONLY.match(text):
        return (ConversationDetectedIntent.greeting, 0.92)
    if len(text) <= 72 and _UZ_GREETING.match(text):
        return (ConversationDetectedIntent.greeting, 0.9)

    if len(text) <= 32 and _SHORT_ACK_ONLY.match(text):
        return (ConversationDetectedIntent.sales_interest, 0.78)

    lower = text.lower()

    # Order: more specific business intents before generic FAQ.
    if _SUPPORT_MARKERS.search(lower):
        return (ConversationDetectedIntent.support, 0.88)
    if _CONSULTING_MARKERS.search(lower):
        return (ConversationDetectedIntent.consulting, 0.85)
    if _SALES_MARKERS.search(lower):
        return (ConversationDetectedIntent.sales_interest, 0.85)
    if _BOOKING_MARKERS.search(lower):
        return (ConversationDetectedIntent.sales_interest, 0.84)
    if _CONTACT_MARKERS.search(lower):
        return (ConversationDetectedIntent.sales_interest, 0.83)
    if _AVAILABILITY_MARKERS.search(lower):
        return (ConversationDetectedIntent.sales_interest, 0.82)
    if _FAQ_MARKERS.search(lower):
        return (ConversationDetectedIntent.faq, 0.78)

    # Regional / niche phrasing: treat clear “need service” utterances as sales_interest
    # (lead-style) before deferring to the model.
    if _UZ_EDUCATION_NEED.search(text):
        return (ConversationDetectedIntent.sales_interest, 0.8)
    if _UZ_HEALTHCARE_BOOKING.search(text):
        return (ConversationDetectedIntent.sales_interest, 0.82)
    if _UZ_DIGITAL_COMMERCE.search(text):
        return (ConversationDetectedIntent.sales_interest, 0.83)
    if _UZ_HOME_TRADES.search(text):
        return (ConversationDetectedIntent.sales_interest, 0.82)

    return None


def is_rule_engine_opening_or_ack(message: str) -> bool:
    """True for greeting-only / Uzbek salutation / short funnel ack lines (same family as rules, no model)."""
    text = (message or "").strip()
    if not text:
        return False
    if len(text) <= 56 and _GREETING_ONLY.match(text):
        return True
    if len(text) <= 72 and _UZ_GREETING.match(text):
        return True
    if len(text) <= 32 and _SHORT_ACK_ONLY.match(text):
        return True
    return False
