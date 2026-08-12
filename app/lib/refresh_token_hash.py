"""SHA-256 hash of raw refresh JWT for server-side lookup (never store plaintext tokens)."""

from __future__ import annotations

import hashlib
import hmac


def hash_refresh_token(raw_token: str) -> str:
    """Return lowercase hex SHA-256 of the exact bearer string (strip outer whitespace only)."""
    body = (raw_token or "").strip().encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def refresh_tokens_equal(a_raw: str, b_hash: str) -> bool:
    """Constant-time compare of raw token to stored hex digest."""
    digest = hash_refresh_token(a_raw)
    return hmac.compare_digest(digest, b_hash)
