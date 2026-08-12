from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any, Literal

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import Settings, get_settings
from app.integrations.storage.base import (
    BodyT,
    ObjectNotFoundError,
    ObjectStorageBackend,
    ObjectStorageError,
)

_CHUNK = 1024 * 1024


def _client_error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", "") or "")


class S3CompatibleObjectStorage(ObjectStorageBackend):
    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        endpoint_url: str | None,
        addressing_style: Literal["path", "virtual"] = "path",
    ) -> None:
        self._bucket = bucket.strip()
        if not self._bucket:
            raise ValueError("bucket must be non-empty")
        botocore_config = BotoConfig(
            signature_version="s3v4",
            s3={"addressing_style": addressing_style},
        )
        self._client: Any = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            endpoint_url=endpoint_url or None,
            config=botocore_config,
        )

    @property
    def bucket(self) -> str:
        return self._bucket

    async def upload_file(
        self,
        *,
        key: str,
        body: BodyT,
        content_type: str | None = None,
        content_length: int | None = None,
    ) -> None:
        extra: dict[str, object] = {}
        if content_type:
            extra["ContentType"] = content_type
        if content_length is not None:
            extra["ContentLength"] = content_length

        def _put() -> None:
            try:
                self._client.put_object(
                    Bucket=self._bucket,
                    Key=key,
                    Body=body,
                    **extra,
                )
            except ClientError as e:
                raise ObjectStorageError(_client_error_code(e) or str(e), key=key) from e

        await asyncio.to_thread(_put)

    async def delete_file(self, *, key: str) -> None:
        def _delete() -> None:
            try:
                self._client.delete_object(Bucket=self._bucket, Key=key)
            except ClientError as e:
                code = _client_error_code(e)
                if code in ("NoSuchKey", "404"):
                    return
                raise ObjectStorageError(code or str(e), key=key) from e

        await asyncio.to_thread(_delete)

    async def get_file_stream(self, *, key: str) -> AsyncIterator[bytes]:
        def _open_stream():
            try:
                resp = self._client.get_object(Bucket=self._bucket, Key=key)
            except ClientError as e:
                code = _client_error_code(e)
                if code in ("NoSuchKey", "404", "NotFound"):
                    raise ObjectNotFoundError(key) from e
                raise ObjectStorageError(code or str(e), key=key) from e
            return resp["Body"]

        body = await asyncio.to_thread(_open_stream)
        try:
            while True:
                chunk = await asyncio.to_thread(body.read, _CHUNK)
                if not chunk:
                    break
                yield chunk
        finally:
            await asyncio.to_thread(body.close)

    async def file_exists(self, *, key: str) -> bool:
        def _head() -> bool:
            try:
                self._client.head_object(Bucket=self._bucket, Key=key)
                return True
            except ClientError as e:
                code = _client_error_code(e)
                if code in ("404", "NoSuchKey", "NotFound"):
                    return False
                raise ObjectStorageError(code or str(e), key=key) from e

        return await asyncio.to_thread(_head)


def object_storage_from_settings(settings: Settings | None = None) -> S3CompatibleObjectStorage | None:
    s = settings or get_settings()
    bucket = (s.object_storage_bucket or "").strip()
    ak = (s.object_storage_access_key_id or "").strip()
    sk = (s.object_storage_secret_access_key or "").strip()
    if not bucket or not ak or not sk:
        return None
    endpoint = (s.object_storage_endpoint_url or "").strip() or None
    return S3CompatibleObjectStorage(
        bucket=bucket,
        region=(s.object_storage_region or "us-east-1").strip(),
        access_key_id=ak,
        secret_access_key=sk,
        endpoint_url=endpoint,
        addressing_style=s.object_storage_addressing_style,
    )
