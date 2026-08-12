"""
Short-lived token store for email verification and password reset.

Tokens are stored in Redis with TTL — single-use (deleted on consumption).
No database columns required.

Key schema
----------
Email verification : ``bf:ev:{token}``  → user_id  (TTL 24 h)
Password reset     : ``bf:pr:{token}``  → user_id  (TTL  1 h)
"""

from __future__ import annotations

import secrets
import uuid
from typing import Literal

import redis.asyncio as aioredis

from app.core.logging import get_logger

_LOG = get_logger(__name__)

TokenKind = Literal["email_verify", "password_reset"]

_PREFIX: dict[TokenKind, str] = {
    "email_verify": "bf:ev:",
    "password_reset": "bf:pr:",
}


class EmailTokenService:
    """
    Create and consume single-use Redis tokens.

    Inject a ``redis.asyncio.Redis`` client (or ``None`` for unit tests
    that don't touch Redis).
    """

    def __init__(self, redis_client: aioredis.Redis | None) -> None:
        self._r = redis_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_token(
        self,
        kind: TokenKind,
        user_id: uuid.UUID,
        ttl_seconds: int,
    ) -> str:
        """
        Generate a URL-safe token, store it in Redis with ``ttl_seconds``,
        and return the raw token string.

        Raises ``RuntimeError`` when Redis is unavailable.
        """
        if self._r is None:
            raise RuntimeError("Redis is not available — cannot create email token")

        token = secrets.token_urlsafe(32)
        key = _PREFIX[kind] + token
        try:
            await self._r.set(key, str(user_id), ex=ttl_seconds)
        except aioredis.RedisError as exc:
            _LOG.warning(
                "email_token_create_failed",
                kind=kind,
                error=str(exc)[:120],
            )
            raise RuntimeError("Failed to store email token in Redis") from exc

        _LOG.debug("email_token_created", kind=kind, ttl_seconds=ttl_seconds)
        return token

    async def consume_token(
        self,
        kind: TokenKind,
        token: str,
    ) -> uuid.UUID | None:
        """
        Validate ``token`` and return the associated ``user_id``.

        Returns ``None`` when the token is missing, expired, or invalid.
        On success the token is deleted (single-use).
        """
        if self._r is None or not (token or "").strip():
            return None

        key = _PREFIX[kind] + token.strip()
        try:
            raw = await self._r.getdel(key)
        except aioredis.RedisError as exc:
            _LOG.warning(
                "email_token_consume_failed",
                kind=kind,
                error=str(exc)[:120],
            )
            return None

        if not raw:
            _LOG.debug("email_token_not_found_or_expired", kind=kind)
            return None

        try:
            uid = uuid.UUID(str(raw))
        except (ValueError, AttributeError):
            _LOG.warning("email_token_invalid_user_id_stored", kind=kind, raw=str(raw)[:40])
            return None

        _LOG.debug("email_token_consumed", kind=kind)
        return uid

    async def revoke_token(self, kind: TokenKind, token: str) -> None:
        """Explicitly delete a token (e.g. after password change)."""
        if self._r is None or not (token or "").strip():
            return
        try:
            await self._r.delete(_PREFIX[kind] + token.strip())
        except aioredis.RedisError:
            pass
