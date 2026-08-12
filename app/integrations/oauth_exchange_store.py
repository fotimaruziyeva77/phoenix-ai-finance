"""Short-lived, one-time codes that map to serialized session payloads (in-process MVP)."""

from __future__ import annotations

import secrets
import threading
import time


class OAuthExchangeStore:
    """
    Single-process exchange codes (TTL + one use).

    For multi-worker production, replace with Redis or a database table.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, tuple[float, str]] = {}

    def _prune_locked(self) -> None:
        now = time.time()
        for key, (deadline, _) in list(self._entries.items()):
            if deadline <= now:
                del self._entries[key]

    def put(self, payload: str, *, ttl_seconds: int = 120) -> str:
        code = secrets.token_urlsafe(32)
        deadline = time.time() + ttl_seconds
        with self._lock:
            self._prune_locked()
            self._entries[code] = (deadline, payload)
        return code

    def pop(self, code: str) -> str | None:
        if not code or len(code.strip()) < 8:
            return None
        key = code.strip()
        with self._lock:
            self._prune_locked()
            item = self._entries.pop(key, None)
        if item is None:
            return None
        deadline, payload = item
        if time.time() > deadline:
            return None
        return payload
