"""Opaque visitor session identifiers for public web widget conversations (privacy-preserving)."""

from __future__ import annotations

import re
import secrets
import uuid

# Server-issued default length; clients may send UUID or similar opaque ids.
_MIN_KEY_LEN = 16
_MAX_KEY_LEN = 64
_VISITOR_KEY_RE = re.compile(rf"^[A-Za-z0-9_-]{{{_MIN_KEY_LEN},{_MAX_KEY_LEN}}}$")


def normalize_or_generate_visitor_session_key(raw: str | None) -> str:
    """
    Return a stable opaque key for multi-turn / reconnect.

    * ``None`` / blank → new URL-safe token (client should persist it).
    * Valid UUID string → canonical ``str(UUID)``.
    * Otherwise must match ``[A-Za-z0-9_-]{16,64}`` (no PII, no structured identity).
    """
    if raw is None or not str(raw).strip():
        return secrets.token_urlsafe(24)

    s = str(raw).strip()
    try:
        return str(uuid.UUID(s))
    except ValueError:
        pass

    if _VISITOR_KEY_RE.fullmatch(s):
        return s

    raise ValueError(
        "visitor_session_key must be a UUID or a 16–64 character alphanumeric / -_ token",
    )


def sanitize_visitor_client_hint(raw: str | None, *, max_len: int = 128) -> str | None:
    """
    Optional non-PII client label (e.g. install-scoped random id prefix).

    Strips whitespace; rejects empty; truncates; no newlines.
    """
    if raw is None:
        return None
    s = " ".join(str(raw).split())
    if not s:
        return None
    s = s.replace("\r", "").replace("\n", "").strip()
    if not s:
        return None
    return s[:max_len]
