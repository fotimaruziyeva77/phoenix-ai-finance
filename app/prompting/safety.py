"""Strip secret-shaped substrings before text enters model prompts."""

from __future__ import annotations

import re

# Google API–style keys, common sk-* secrets, Bearer tokens in user paste
_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{20,}", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key|apikey|password|secret)\s*[:=]\s*\S{8,}"),
)

_REDACT = "[REDACTED]"


def scrub_secrets_for_prompt(text: str) -> str:
    """Best-effort redaction for user-controlled or echoed content."""
    if not text:
        return text
    out = text
    for pat in _PATTERNS:
        out = pat.sub(_REDACT, out)
    return out
