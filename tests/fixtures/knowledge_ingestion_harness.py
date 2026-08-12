"""
Shared harness for knowledge ingestion integration tests.

Isolation strategy (used by ``tests.test_knowledge_ingestion_integration``):

* **Real PostgreSQL** via ``TEST_DATABASE_URL`` / host ``DATABASE_URL`` (same rules as
  ``tests.integration_db.integration_database_url``).
* **Real ingestion code path**: :class:`~app.services.knowledge_file_processing_service.KnowledgeFileProcessingService`
  runs unchanged; only **object storage** is swapped for an in-process round-trip backend so
  upload and worker read the same PDF bytes without MinIO.
* **Real queue semantics** on **fakeredis** (async Redis API): LPUSH/BRPOP match production
  layout; worker drain uses the same ``dequeue_and_process_one`` entrypoint as the worker process.
* **Per-test / per-fixture state**: a new ``FakeRedis`` instance and storage dict per test using
  the queue fixture; ``get_settings`` cache cleared and async engine disposed when spinning up
  ``TestClient`` so env and DB pool match the patched URL.

Optional **fault injection** (failure/retry/dead-letter tests only): patch
``extract_pdf_text_by_page`` on the processing **module** — extraction is intentionally pluggable
for tests; chunking, SQL, and status transitions stay real.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, BinaryIO, Union

import asyncpg
import fakeredis.aioredis
import pytest
from app.core.config import get_settings
from app.core.knowledge_ingestion_pipeline import dequeue_and_process_one
from app.core.knowledge_ingestion_queue import (
    RedisKnowledgeIngestionQueue,
    reset_knowledge_ingestion_redis_client_for_tests,
)
from app.integrations.storage.base import ObjectNotFoundError, ObjectStorageBackend
from fastapi.testclient import TestClient

BodyT = Union[bytes, BinaryIO]

JWT_INTEGRATION_KEY = "x" * 32


def asyncpg_dsn(async_pg_url: str) -> str:
    if "+asyncpg" in async_pg_url:
        return async_pg_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return async_pg_url


class RoundTripObjectStorage(ObjectStorageBackend):
    """Uploads populate a dict; processing reads the same bytes back (no MinIO)."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    @property
    def bucket(self) -> str:
        return "integration-roundtrip"

    async def upload_file(
        self,
        *,
        key: str,
        body: BodyT,
        content_type: str | None = None,
        content_length: int | None = None,
    ) -> None:
        if isinstance(body, bytes):
            self.objects[key] = body
        else:
            self.objects[key] = body.read()

    async def delete_file(self, *, key: str) -> None:
        self.objects.pop(key, None)

    async def file_exists(self, *, key: str) -> bool:
        return key in self.objects

    async def get_file_stream(self, *, key: str):
        if key not in self.objects:
            raise ObjectNotFoundError(key)
        yield self.objects[key]


def install_fakeredis_ingestion_queue(monkeypatch: pytest.MonkeyPatch) -> RedisKnowledgeIngestionQueue:
    """Patch queue factory to a dedicated FakeRedis backend (test isolation)."""
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    q = RedisKnowledgeIngestionQueue(r, f"knowledge-ingestion-test-{uuid.uuid4().hex}")

    async def _from_settings(_settings) -> RedisKnowledgeIngestionQueue:
        return q

    monkeypatch.setattr(
        "app.core.knowledge_ingestion_queue.knowledge_ingestion_queue_from_settings",
        _from_settings,
    )
    return q


def teardown_ingestion_queue_client() -> None:
    reset_knowledge_ingestion_redis_client_for_tests()


async def fetch_knowledge_file_row(db_url: str, file_id: uuid.UUID) -> asyncpg.Record | None:
    conn = await asyncpg.connect(dsn=asyncpg_dsn(db_url))
    try:
        return await conn.fetchrow(
            """
            SELECT id, bot_id, owner_id, processing_status, processing_error,
                   page_count, ingestion_failure_count, original_filename
            FROM knowledge_files
            WHERE id = $1
            """,
            file_id,
        )
    finally:
        await conn.close()


async def fetch_knowledge_chunks_for_file(db_url: str, file_id: uuid.UUID) -> list[asyncpg.Record]:
    conn = await asyncpg.connect(dsn=asyncpg_dsn(db_url))
    try:
        rows = await conn.fetch(
            """
            SELECT id, chunk_index, page_number, content, token_count
            FROM knowledge_chunks
            WHERE knowledge_file_id = $1
            ORDER BY chunk_index ASC
            """,
            file_id,
        )
        return list(rows)
    finally:
        await conn.close()


async def count_fts_matching_chunks(db_url: str, file_id: uuid.UUID, query: str) -> int:
    """
    Rows where stored ``content`` matches the query under the same FTS config as the app (``simple``).
    This is the persisted search surface (MVP has **no** separate embedding table).
    """
    conn = await asyncpg.connect(dsn=asyncpg_dsn(db_url))
    try:
        val = await conn.fetchval(
            """
            SELECT COUNT(*)::int
            FROM knowledge_chunks
            WHERE knowledge_file_id = $1
              AND to_tsvector('simple', content) @@ websearch_to_tsquery('simple', $2)
            """,
            file_id,
            query,
        )
        return int(val or 0)
    finally:
        await conn.close()


async def drain_ingestion_worker_once() -> bool:
    """One non-blocking dequeue + full ``KnowledgeFileProcessingService`` run + retry/DL policy."""
    from app.core.knowledge_ingestion_queue import knowledge_ingestion_queue_from_settings

    settings = get_settings()
    q = await knowledge_ingestion_queue_from_settings(settings)
    assert q is not None
    return await dequeue_and_process_one(settings=settings, queue=q)


def drain_ingestion_worker_once_sync() -> bool:
    return asyncio.run(drain_ingestion_worker_once())


def register_user_and_token(client: TestClient, *, prefix: str = "k-ing") -> tuple[str, str]:
    """Returns ``(access_token, email)``."""
    email = f"{prefix}_{uuid.uuid4().hex}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "K Ingest"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"]), email


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def create_bot(client: TestClient, token: str, *, name: str = "K Bot") -> str:
    r = client.post(
        "/api/v1/bots",
        headers=auth_headers(token),
        json={"name": name, "niche_id": "education", "goal_type": "faq"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def upload_pdf(
    client: TestClient,
    *,
    token: str,
    bot_id: str,
    pdf_bytes: bytes,
    filename: str = "doc.pdf",
) -> dict[str, Any]:
    r = client.post(
        f"/api/v1/bots/{bot_id}/knowledge/files",
        headers=auth_headers(token),
        files={"file": (filename, pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 201, r.text
    return r.json()
