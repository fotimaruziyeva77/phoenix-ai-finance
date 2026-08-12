"""Helpers to read full object bytes from storage (bounded)."""

from __future__ import annotations

from app.integrations.storage.base import ObjectStorageBackend, ObjectStorageError


class ObjectTooLargeError(ObjectStorageError):
    def __init__(self, *, key: str, max_bytes: int) -> None:
        super().__init__(f"Object exceeds max_bytes={max_bytes}", key=key)
        self.max_bytes = max_bytes


async def read_object_bytes_bounded(
    storage: ObjectStorageBackend,
    *,
    key: str,
    max_bytes: int,
) -> bytes:
    """Read the entire object, failing if ``max_bytes`` would be exceeded."""
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")

    parts: list[bytes] = []
    total = 0
    async for piece in storage.get_file_stream(key=key):
        total += len(piece)
        if total > max_bytes:
            raise ObjectTooLargeError(key=key, max_bytes=max_bytes)
        parts.append(piece)
    return b"".join(parts)
