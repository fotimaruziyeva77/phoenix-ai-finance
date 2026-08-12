"""
End-to-end integration tests for async knowledge ingestion (upload → queue → worker → DB → retrieve).

**Isolation** (see also ``tests.fixtures.knowledge_ingestion_harness``):

* **PostgreSQL**: real DB via ``TEST_DATABASE_URL`` or host-safe ``DATABASE_URL``; Alembic head once per module.
* **Ingestion pipeline**: real ``KnowledgeFileProcessingService`` (extract → chunk → SQL); only **storage**
  is replaced with ``RoundTripObjectStorage`` so the API and worker share PDF bytes without S3/MinIO.
* **Queue**: fakeredis with the same LPUSH/BRPOP contract as production Redis; drain uses
  ``dequeue_and_process_one`` (same as ``knowledge_ingestion_worker``).
* **Fault injection** (failure / retry / DL only): patch ``extract_pdf_text_by_page`` on the processing
  module — chunking, repositories, commits, retry/dead-letter policy stay unmocked.

**Embeddings**: MVP stores **text chunks** only; retrieval uses PostgreSQL FTS (GIN on
``to_tsvector('simple', content)``). There is no separate embedding table — see
``tests/test_knowledge_ingestion_mvp_unit.py`` and deployment docs.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import NoReturn

import pytest
from app.core.config import get_settings
from app.core.db import dispose_engine
from app.main import app
from app.services.knowledge_pdf_text_extraction import extract_pdf_text_by_page
from fastapi.testclient import TestClient

from tests.db_alembic import run_alembic_upgrade_head
from tests.fixtures.knowledge_ingestion_harness import (
    JWT_INTEGRATION_KEY,
    RoundTripObjectStorage,
    auth_headers,
    count_fts_matching_chunks,
    create_bot,
    drain_ingestion_worker_once_sync,
    fetch_knowledge_chunks_for_file,
    fetch_knowledge_file_row,
    install_fakeredis_ingestion_queue,
    register_user_and_token,
    teardown_ingestion_queue_client,
    upload_pdf,
)
from tests.fixtures.knowledge_pdf_samples import hello_pdf
from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _integration_db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.knowledge_ingestion_e2e,
    pytest.mark.skipif(
        not _integration_db_url(),
        reason=(
            "Set TEST_DATABASE_URL (recommended) or host-reachable DATABASE_URL "
            "(not @postgres: — use 127.0.0.1 when testing from the host)."
        ),
    ),
]


@pytest.fixture(scope="module", autouse=True)
def _alembic_for_knowledge_ingestion() -> None:
    url = _integration_db_url()
    assert url is not None
    run_alembic_upgrade_head(database_url=url, project_root=PROJECT_ROOT)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def ingestion_queue_stub(monkeypatch: pytest.MonkeyPatch):
    q = install_fakeredis_ingestion_queue(monkeypatch)
    yield q
    teardown_ingestion_queue_client()


@pytest.fixture
def kf_ingestion_client(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
    ingestion_queue_stub,  # noqa: ARG001 — installs queue patch
) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("APP_RATE_LIMITING_ENABLED", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "integration-placeholder-key")
    get_settings.cache_clear()
    storage = RoundTripObjectStorage()
    monkeypatch.setattr(
        "app.services.bot_knowledge_file_service.object_storage_from_settings",
        lambda *_a, **_kw: storage,
    )
    monkeypatch.setattr(
        "app.services.knowledge_file_processing_service.object_storage_from_settings",
        lambda *_a, **_kw: storage,
    )
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def test_e2e_knowledge_pipeline_upload_queue_worker_chunks_fts_retrieval(
    kf_ingestion_client: TestClient,
    live_db_url: str,
    ingestion_queue_stub,
) -> None:
    """
    Single trace through the full happy path with **database and FTS assertions**.

    Covers: document upload, job enqueue, worker pickup (drain), extraction success,
    chunk persistence, FTS-visible persisted text, job status API, retrieval API.
    """
    token, _ = register_user_and_token(kf_ingestion_client, prefix="e2e")
    bot_id = create_bot(kf_ingestion_client, token, name="E2E Bot")
    pdf = hello_pdf()

    up = upload_pdf(
        kf_ingestion_client,
        token=token,
        bot_id=bot_id,
        pdf_bytes=pdf,
    )
    file_id = uuid.UUID(up["id"])
    assert up["processing_status"] == "uploaded"

    assert asyncio.run(ingestion_queue_stub.queued_count()) == 1

    row0 = asyncio.run(fetch_knowledge_file_row(live_db_url, file_id))
    assert row0 is not None
    assert row0["processing_status"] == "uploaded"
    assert int(row0["ingestion_failure_count"]) == 0
    assert row0["processing_error"] is None

    chunks0 = asyncio.run(fetch_knowledge_chunks_for_file(live_db_url, file_id))
    assert chunks0 == []

    ing0 = kf_ingestion_client.get(
        f"/api/v1/bots/{bot_id}/knowledge/files/{file_id}/ingestion",
        headers=auth_headers(token),
    )
    assert ing0.status_code == 200, ing0.text
    assert ing0.json()["status"] == "pending"
    assert ing0.json()["searchable"] is False

    assert drain_ingestion_worker_once_sync() is True
    assert asyncio.run(ingestion_queue_stub.queued_count()) == 0

    row1 = asyncio.run(fetch_knowledge_file_row(live_db_url, file_id))
    assert row1 is not None
    assert row1["processing_status"] == "ready"
    assert row1["processing_error"] is None
    assert int(row1["ingestion_failure_count"]) == 0
    assert row1["page_count"] is not None and int(row1["page_count"]) >= 1

    chunks1 = asyncio.run(fetch_knowledge_chunks_for_file(live_db_url, file_id))
    assert len(chunks1) >= 1
    joined = " ".join(str(c["content"]) for c in chunks1)
    assert "Hello" in joined and "PDF" in joined
    assert all(c["token_count"] is None or int(c["token_count"]) >= 0 for c in chunks1)

    fts_hits = asyncio.run(count_fts_matching_chunks(live_db_url, file_id, "Hello PDF"))
    assert fts_hits >= 1

    ing1 = kf_ingestion_client.get(
        f"/api/v1/bots/{bot_id}/knowledge/files/{file_id}/ingestion",
        headers=auth_headers(token),
    )
    assert ing1.json()["status"] == "completed"
    assert ing1.json()["processing_status"] == "ready"
    assert ing1.json()["searchable"] is True

    ret = kf_ingestion_client.post(
        f"/api/v1/bots/{bot_id}/knowledge/retrieve",
        headers=auth_headers(token),
        json={"query": "Hello PDF"},
    )
    assert ret.status_code == 200, ret.text
    assert len(ret.json()["hits"]) >= 1


def test_upload_enqueues_job_message(kf_ingestion_client: TestClient, ingestion_queue_stub) -> None:
    token, _ = register_user_and_token(kf_ingestion_client, prefix="enqueue")
    bot_id = create_bot(kf_ingestion_client, token)
    upload_pdf(kf_ingestion_client, token=token, bot_id=bot_id, pdf_bytes=hello_pdf())
    assert asyncio.run(ingestion_queue_stub.queued_count()) == 1


def test_extraction_failure_increments_counter_requeues_visible_in_db(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
) -> None:
    q = install_fakeredis_ingestion_queue(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("APP_RATE_LIMITING_ENABLED", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "integration-placeholder-key")
    monkeypatch.setenv("APP_KNOWLEDGE_INGESTION_MAX_ATTEMPTS", "3")
    get_settings.cache_clear()
    storage = RoundTripObjectStorage()
    monkeypatch.setattr(
        "app.services.bot_knowledge_file_service.object_storage_from_settings",
        lambda *_a, **_kw: storage,
    )
    monkeypatch.setattr(
        "app.services.knowledge_file_processing_service.object_storage_from_settings",
        lambda *_a, **_kw: storage,
    )

    def boom(_pdf: bytes) -> NoReturn:
        raise RuntimeError("forced extraction failure")

    monkeypatch.setattr(
        "app.services.knowledge_file_processing_service.extract_pdf_text_by_page",
        boom,
    )

    asyncio.run(dispose_engine())
    try:
        with TestClient(app) as client:
            token, _ = register_user_and_token(client, prefix="fail")
            bot_id = create_bot(client, token)
            body = upload_pdf(client, token=token, bot_id=bot_id, pdf_bytes=hello_pdf())
            fid = uuid.UUID(body["id"])

            assert drain_ingestion_worker_once_sync() is True
            r1 = asyncio.run(fetch_knowledge_file_row(live_db_url, fid))
            assert r1["processing_status"] == "failed"
            assert r1["processing_error"] is not None
            assert int(r1["ingestion_failure_count"]) == 1
            assert asyncio.run(fetch_knowledge_chunks_for_file(live_db_url, fid)) == []
            assert asyncio.run(q.queued_count()) == 1

            assert drain_ingestion_worker_once_sync() is True
            r2 = asyncio.run(fetch_knowledge_file_row(live_db_url, fid))
            assert int(r2["ingestion_failure_count"]) == 2
            assert asyncio.run(q.queued_count()) == 1
    finally:
        asyncio.run(dispose_engine())
        teardown_ingestion_queue_client()
        get_settings.cache_clear()


def test_dead_letter_stops_retries_and_leaves_no_chunks(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
) -> None:
    q = install_fakeredis_ingestion_queue(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("APP_RATE_LIMITING_ENABLED", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "integration-placeholder-key")
    monkeypatch.setenv("APP_KNOWLEDGE_INGESTION_MAX_ATTEMPTS", "2")
    get_settings.cache_clear()
    storage = RoundTripObjectStorage()
    monkeypatch.setattr(
        "app.services.bot_knowledge_file_service.object_storage_from_settings",
        lambda *_a, **_kw: storage,
    )
    monkeypatch.setattr(
        "app.services.knowledge_file_processing_service.object_storage_from_settings",
        lambda *_a, **_kw: storage,
    )

    def boom(_pdf: bytes) -> NoReturn:
        raise RuntimeError("forced extraction failure")

    monkeypatch.setattr(
        "app.services.knowledge_file_processing_service.extract_pdf_text_by_page",
        boom,
    )

    asyncio.run(dispose_engine())
    try:
        with TestClient(app) as client:
            token, _ = register_user_and_token(client, prefix="dl")
            bot_id = create_bot(client, token)
            body = upload_pdf(client, token=token, bot_id=bot_id, pdf_bytes=hello_pdf())
            fid = uuid.UUID(body["id"])

            assert drain_ingestion_worker_once_sync() is True
            assert asyncio.run(fetch_knowledge_file_row(live_db_url, fid))["processing_status"] == "failed"

            assert drain_ingestion_worker_once_sync() is True
            r_dl = asyncio.run(fetch_knowledge_file_row(live_db_url, fid))
            assert r_dl["processing_status"] == "dead_letter"
            assert int(r_dl["ingestion_failure_count"]) == 2
            assert asyncio.run(q.queued_count()) == 0
            assert asyncio.run(fetch_knowledge_chunks_for_file(live_db_url, fid)) == []

            st = client.get(
                f"/api/v1/bots/{bot_id}/knowledge/files/{fid}/ingestion",
                headers=auth_headers(token),
            )
            assert st.json()["status"] == "dead_letter"
            assert st.json()["searchable"] is False
    finally:
        asyncio.run(dispose_engine())
        teardown_ingestion_queue_client()
        get_settings.cache_clear()


def test_retry_recovers_after_transient_extraction_error(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
) -> None:
    q = install_fakeredis_ingestion_queue(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("APP_RATE_LIMITING_ENABLED", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "integration-placeholder-key")
    get_settings.cache_clear()
    storage = RoundTripObjectStorage()
    monkeypatch.setattr(
        "app.services.bot_knowledge_file_service.object_storage_from_settings",
        lambda *_a, **_kw: storage,
    )
    monkeypatch.setattr(
        "app.services.knowledge_file_processing_service.object_storage_from_settings",
        lambda *_a, **_kw: storage,
    )

    calls = {"n": 0}

    def flaky_extract(pdf: bytes) -> tuple[int, list[str]]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return extract_pdf_text_by_page(pdf)

    monkeypatch.setattr(
        "app.services.knowledge_file_processing_service.extract_pdf_text_by_page",
        flaky_extract,
    )

    asyncio.run(dispose_engine())
    try:
        with TestClient(app) as client:
            token, _ = register_user_and_token(client, prefix="retry")
            bot_id = create_bot(client, token)
            body = upload_pdf(client, token=token, bot_id=bot_id, pdf_bytes=hello_pdf())
            fid = uuid.UUID(body["id"])

            assert drain_ingestion_worker_once_sync() is True
            assert asyncio.run(fetch_knowledge_file_row(live_db_url, fid))["processing_status"] == "failed"
            assert asyncio.run(q.queued_count()) == 1

            assert drain_ingestion_worker_once_sync() is True
            r_ok = asyncio.run(fetch_knowledge_file_row(live_db_url, fid))
            assert r_ok["processing_status"] == "ready"
            assert int(r_ok["ingestion_failure_count"]) == 0
            assert len(asyncio.run(fetch_knowledge_chunks_for_file(live_db_url, fid))) >= 1
            assert asyncio.run(q.queued_count()) == 0
    finally:
        asyncio.run(dispose_engine())
        teardown_ingestion_queue_client()
        get_settings.cache_clear()


def test_retrieval_empty_until_ready(kf_ingestion_client: TestClient, ingestion_queue_stub) -> None:
    token, _ = register_user_and_token(kf_ingestion_client, prefix="retrieve")
    bot_id = create_bot(kf_ingestion_client, token)
    upload_pdf(kf_ingestion_client, token=token, bot_id=bot_id, pdf_bytes=hello_pdf())

    before = kf_ingestion_client.post(
        f"/api/v1/bots/{bot_id}/knowledge/retrieve",
        headers=auth_headers(token),
        json={"query": "Hello PDF"},
    )
    assert before.json()["hits"] == []

    assert drain_ingestion_worker_once_sync() is True

    after = kf_ingestion_client.post(
        f"/api/v1/bots/{bot_id}/knowledge/retrieve",
        headers=auth_headers(token),
        json={"query": "Hello PDF"},
    )
    assert len(after.json()["hits"]) >= 1


def test_ingestion_status_forbidden_for_non_owner(kf_ingestion_client: TestClient) -> None:
    ta, _ = register_user_and_token(kf_ingestion_client, prefix="a")
    tb, _ = register_user_and_token(kf_ingestion_client, prefix="b")
    bot_a = create_bot(kf_ingestion_client, ta)
    create_bot(kf_ingestion_client, tb)
    body = upload_pdf(kf_ingestion_client, token=ta, bot_id=bot_a, pdf_bytes=hello_pdf())
    fid = body["id"]
    r = kf_ingestion_client.get(
        f"/api/v1/bots/{bot_a}/knowledge/files/{fid}/ingestion",
        headers=auth_headers(tb),
    )
    assert r.status_code == 404
    assert r.json().get("error", {}).get("code") == "bot_not_found"
