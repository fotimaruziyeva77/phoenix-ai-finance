from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import BinaryIO, Union

BodyT = Union[bytes, BinaryIO]


class ObjectStorageError(Exception):
    def __init__(self, message: str, *, key: str | None = None) -> None:
        super().__init__(message)
        self.key = key


class ObjectNotFoundError(ObjectStorageError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Object not found: {key}", key=key)


class ObjectStorageBackend(ABC):
    @property
    @abstractmethod
    def bucket(self) -> str: ...

    @abstractmethod
    async def upload_file(
        self,
        *,
        key: str,
        body: BodyT,
        content_type: str | None = None,
        content_length: int | None = None,
    ) -> None: ...

    @abstractmethod
    async def delete_file(self, *, key: str) -> None: ...

    @abstractmethod
    async def get_file_stream(self, *, key: str) -> AsyncIterator[bytes]: ...

    @abstractmethod
    async def file_exists(self, *, key: str) -> bool: ...
