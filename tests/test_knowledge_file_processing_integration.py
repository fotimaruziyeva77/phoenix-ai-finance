"""
PDF processing pipeline integration tests (status transitions, chunks, retries).

Requires PostgreSQL + Alembic head (``TEST_DATABASE_URL`` or host-reachable ``DATABASE_URL``).

Covers:
  * ``uploaded`` / ``failed`` → ``processing`` (claim)
  * ``processing`` → ``ready`` with chunks + ``page_count``
  * ``processing`` → ``failed`` with ``processing_error``
  * Safe rerun from ``failed`` and idempotent skip when ``ready``
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from app.core.config import Settings, get_settings
from app.core.db import dispose_engine, get_session_maker
from app.integrations.storage import knowledge_file_object_key
from app.integrations.storage.base import ObjectNotFoundError, ObjectStorageBackend
from app.models.bot import Bot
from app.models.enums import UserRole
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_file import KnowledgeFile
from app.models.user import User
from app.repositories.knowledge_file_repository import KnowledgeFileRepository
from app.services.knowledge_file_processing_service import (
    KnowledgeFileProcessingOutcome,
    KnowledgeFileProcessingService,
)
from app.services.knowledge_pdf_text_extraction import extract_pdf_text_by_page
from sqlalchemy import select, update

from tests.db_alembic import run_alembic_upgrade_head
from tests.fixtures.knowledge_pdf_samples import hello_pdf, two_page_hello_pdf
from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _integration_db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.knowledge_processing,
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not _integration_db_url(),
        reason=(
            "Set TEST_DATABASE_URL (recommended) or host-reachable DATABASE_URL "
            "(not @postgres: — use 127.0.0.1 when testing from the host)."
        ),
    ),
]


@pytest.fixture(scope="module", autouse=True)
def _alembic_for_processing_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    run_alembic_upgrade_head(database_url=url, project_root=PROJECT_ROOT)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


class _MemoryStorage(ObjectStorageBackend):
    def __init__(self, data: bytes) -> None:
        self._data = data

    @property
    def bucket(self) -> str:
        return "test-bucket"

    async def upload_file(self, *, key: str, body, content_type: str | None = None, content_length: int | None = None) -> None:  # noqa: ANN001
        raise NotImplementedError

    async def delete_file(self, *, key: str) -> None:
        raise NotImplementedError

    async def file_exists(self, *, key: str) -> bool:
        return True

    async def get_file_stream(self, *, key: str):
        yield self._data


class _MemoryStorageByKey(ObjectStorageBackend):
    """Serve PDF bytes per object key (multi-file same-bot tests)."""

    def __init__(self, by_key: dict[str, bytes]) -> None:
        self._by_key = by_key

    @property
    def bucket(self) -> str:
        return "test-bucket"

    async def upload_file(self, *, key: str, body, content_type: str | None = None, content_length: int | None = None) -> None:  # noqa: ANN001
        raise NotImplementedError

    async def delete_file(self, *, key: str) -> None:
        raise NotImplementedError

    async def file_exists(self, *, key: str) -> bool:
        return key in self._by_key

    async def get_file_stream(self, *, key: str):
        if key not in self._by_key:
            raise ObjectNotFoundError(key)
        yield self._by_key[key]


class _MissingObjectStorage(ObjectStorageBackend):
    """Storage backend that simulates a missing object key."""

    @property
    def bucket(self) -> str:
        return "test-bucket"

    async def upload_file(self, *, key: str, body, content_type: str | None = None, content_length: int | None = None) -> None:  # noqa: ANN001
        raise NotImplementedError

    async def delete_file(self, *, key: str) -> None:
        raise NotImplementedError

    async def file_exists(self, *, key: str) -> bool:
        return False

    async def get_file_stream(self, *, key: str):
        raise ObjectNotFoundError(key)
        yield b""  # pragma: no cover


async def _seed_knowledge_file(
    session_maker,
    *,
    pdf_bytes: bytes,
    processing_status: str = "uploaded",
    processing_error: str | None = None,
    mime_type: str = "application/pdf",
) -> uuid.UUID:
    uid = uuid.uuid4()
    bid = uuid.uuid4()
    fid = uuid.uuid4()
    storage_key = f"v1/knowledge/test/{fid}/doc.pdf"

    async with session_maker() as session:
        user = User(
            id=uid,
            email=f"proc_{uuid.uuid4().hex}@example.com",
            password_hash="x",
            role=UserRole.customer_admin,
        )
        bot = Bot(
            id=bid,
            owner_id=uid,
            name="Proc Bot",
            niche_id="education",
            goal_type="faq",
        )
        kf = KnowledgeFile(
            id=fid,
            bot_id=bid,
            owner_id=uid,
            original_filename="doc.pdf",
            storage_key=storage_key,
            mime_type=mime_type,
            file_size_bytes=len(pdf_bytes),
            processing_status=processing_status,
            processing_error=processing_error,
        )
        session.add_all([user, bot, kf])
        await session.commit()
    return fid


@pytest.fixture
async def processing_settings(live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    get_settings.cache_clear()
    await dispose_engine()
    return get_settings()


@pytest.fixture
async def session_maker(live_db_url: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    get_settings.cache_clear()
    await dispose_engine()
    yield get_session_maker()
    await dispose_engine()
    get_settings.cache_clear()


# --- Status transitions (repository claim) ---


async def test_status_uploaded_moves_to_processing_on_claim(session_maker) -> None:
    """1. An uploaded file can move to ``processing`` when a worker claims it."""
    pdf = hello_pdf()
    fid = await _seed_knowledge_file(session_maker, pdf_bytes=pdf, processing_status="uploaded")

    async with session_maker() as session:
        repo = KnowledgeFileRepository(session)
        row = await repo.try_claim_for_processing(fid)
        assert row is not None
        assert row.processing_status == "processing"
        assert row.processing_error is None
        await session.commit()

    async with session_maker() as session:
        kf = await session.get(KnowledgeFile, fid)
        assert kf is not None
        assert kf.processing_status == "processing"


async def test_status_failed_moves_to_processing_on_claim_and_clears_error(session_maker) -> None:
    """Rerun design: ``failed`` rows are claimable; prior ``processing_error`` is cleared on claim."""
    pdf = hello_pdf()
    fid = await _seed_knowledge_file(
        session_maker,
        pdf_bytes=pdf,
        processing_status="failed",
        processing_error="previous failure",
    )

    async with session_maker() as session:
        repo = KnowledgeFileRepository(session)
        row = await repo.try_claim_for_processing(fid)
        assert row is not None
        assert row.processing_status == "processing"
        assert row.processing_error is None
        await session.commit()


async def test_status_ready_not_claimable(session_maker) -> None:
    pdf = hello_pdf()
    fid = await _seed_knowledge_file(session_maker, pdf_bytes=pdf, processing_status="ready")

    async with session_maker() as session:
        repo = KnowledgeFileRepository(session)
        assert await repo.try_claim_for_processing(fid) is None


async def test_mark_processing_failed_wrong_owner_does_not_mutate_row(session_maker) -> None:
    """Tenant-scoped status update: wrong owner_id or bot_id must match zero rows."""
    pdf = hello_pdf()
    fid = await _seed_knowledge_file(session_maker, pdf_bytes=pdf)

    async with session_maker() as session:
        kf = await session.get(KnowledgeFile, fid)
        assert kf is not None
        bid = kf.bot_id
        oid = kf.owner_id
        repo = KnowledgeFileRepository(session)
        await repo.mark_processing_failed(
            fid,
            owner_id=uuid.uuid4(),
            bot_id=bid,
            message="should not apply",
        )
        await session.commit()

    async with session_maker() as session:
        kf2 = await session.get(KnowledgeFile, fid)
        assert kf2 is not None
        assert kf2.processing_status == "uploaded"
        assert kf2.processing_error is None

    async with session_maker() as session:
        repo = KnowledgeFileRepository(session)
        await repo.mark_processing_failed(
            fid,
            owner_id=oid,
            bot_id=uuid.uuid4(),
            message="wrong bot",
        )
        await session.commit()

    async with session_maker() as session:
        kf3 = await session.get(KnowledgeFile, fid)
        assert kf3 is not None
        assert kf3.processing_status == "uploaded"
        assert kf3.processing_error is None


# --- Full pipeline with sample PDFs ---


async def test_valid_pdf_extraction_creates_chunks_ready_and_page_count(
    session_maker,
    processing_settings: Settings,
) -> None:
    """2–4. Valid PDF → chunk rows, ``page_count`` set, ``ready``."""
    pdf = hello_pdf()
    n_pages, _ = extract_pdf_text_by_page(pdf)
    assert n_pages == 1

    fid = await _seed_knowledge_file(session_maker, pdf_bytes=pdf)
    storage = _MemoryStorage(pdf)

    async with session_maker() as session:
        svc = KnowledgeFileProcessingService(session, processing_settings, storage=storage)
        assert await svc.process_file(fid) == KnowledgeFileProcessingOutcome.READY

    async with session_maker() as session:
        kf = await session.get(KnowledgeFile, fid)
        assert kf is not None
        assert kf.processing_status == "ready"
        assert kf.page_count == 1
        assert kf.processing_error is None

        res = await session.execute(select(KnowledgeChunk).where(KnowledgeChunk.knowledge_file_id == fid))
        chunks = list(res.scalars().all())
        assert len(chunks) >= 1
        assert all(c.chunk_index == i for i, c in enumerate(chunks))
        assert "Hello" in chunks[0].content


async def test_two_page_sample_pdf_page_count_and_chunks(session_maker, processing_settings: Settings) -> None:
    """3–4. Multi-page sample: ``page_count`` matches PDF; chunks include text from pages."""
    pdf = two_page_hello_pdf()
    n_pages, page_texts = extract_pdf_text_by_page(pdf)
    assert n_pages == 2
    assert all("Hello" in t for _, t in page_texts if t)

    fid = await _seed_knowledge_file(session_maker, pdf_bytes=pdf)
    storage = _MemoryStorage(pdf)

    async with session_maker() as session:
        svc = KnowledgeFileProcessingService(session, processing_settings, storage=storage)
        assert await svc.process_file(fid) == KnowledgeFileProcessingOutcome.READY

    async with session_maker() as session:
        kf = await session.get(KnowledgeFile, fid)
        assert kf is not None
        assert kf.processing_status == "ready"
        assert kf.page_count == 2

        res = await session.execute(
            select(KnowledgeChunk).where(KnowledgeChunk.knowledge_file_id == fid).order_by(KnowledgeChunk.chunk_index)
        )
        chunks = list(res.scalars().all())
        assert len(chunks) >= 1
        joined = "\n".join(c.content for c in chunks)
        assert "Hello" in joined


async def test_failure_on_one_file_does_not_corrupt_sibling_ready_file(
    session_maker,
    processing_settings: Settings,
) -> None:
    """If file B fails extraction, file A on the same bot stays ready with chunks."""
    good = hello_pdf()
    bad = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    uid = uuid.uuid4()
    bid = uuid.uuid4()
    fg = uuid.uuid4()
    fb = uuid.uuid4()
    key_good = knowledge_file_object_key(
        owner_id=uid, bot_id=bid, file_id=fg, original_filename="g.pdf"
    )
    key_bad = knowledge_file_object_key(
        owner_id=uid, bot_id=bid, file_id=fb, original_filename="b.pdf"
    )

    async with session_maker() as session:
        user = User(
            id=uid,
            email=f"pair_{uuid.uuid4().hex}@example.com",
            password_hash="x",
            role=UserRole.customer_admin,
        )
        bot = Bot(id=bid, owner_id=uid, name="Pair Bot", niche_id="education", goal_type="faq")
        k_good = KnowledgeFile(
            id=fg,
            bot_id=bid,
            owner_id=uid,
            original_filename="g.pdf",
            storage_key=key_good,
            mime_type="application/pdf",
            file_size_bytes=len(good),
            processing_status="uploaded",
        )
        k_bad = KnowledgeFile(
            id=fb,
            bot_id=bid,
            owner_id=uid,
            original_filename="b.pdf",
            storage_key=key_bad,
            mime_type="application/pdf",
            file_size_bytes=len(bad),
            processing_status="uploaded",
        )
        session.add_all([user, bot, k_good, k_bad])
        await session.commit()

    by_key = {key_good: good, key_bad: bad}
    storage = _MemoryStorageByKey(by_key)

    async with session_maker() as session:
        svc = KnowledgeFileProcessingService(session, processing_settings, storage=storage)
        assert await svc.process_file(fg) == KnowledgeFileProcessingOutcome.READY

    async with session_maker() as session:
        svc = KnowledgeFileProcessingService(session, processing_settings, storage=storage)
        assert await svc.process_file(fb) == KnowledgeFileProcessingOutcome.FAILED

    async with session_maker() as session:
        row_good = await session.get(KnowledgeFile, fg)
        row_bad = await session.get(KnowledgeFile, fb)
        assert row_good is not None and row_bad is not None
        assert row_good.processing_status == "ready"
        assert row_good.page_count == 1
        assert row_bad.processing_status == "failed"
        assert row_bad.processing_error

        res_ok = await session.execute(select(KnowledgeChunk).where(KnowledgeChunk.knowledge_file_id == fg))
        assert len(list(res_ok.scalars().all())) >= 1
        res_fail = await session.execute(select(KnowledgeChunk).where(KnowledgeChunk.knowledge_file_id == fb))
        assert len(list(res_fail.scalars().all())) == 0


async def test_invalid_pdf_marks_failed_with_error(session_maker, processing_settings: Settings) -> None:
    """5. Unreadable PDF → ``failed`` + non-empty ``processing_error``."""
    bad = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    fid = await _seed_knowledge_file(session_maker, pdf_bytes=bad)
    storage = _MemoryStorage(bad)

    async with session_maker() as session:
        svc = KnowledgeFileProcessingService(session, processing_settings, storage=storage)
        assert await svc.process_file(fid) == KnowledgeFileProcessingOutcome.FAILED

    async with session_maker() as session:
        kf = await session.get(KnowledgeFile, fid)
        assert kf is not None
        assert kf.processing_status == "failed"
        assert kf.processing_error
        assert "PDF" in kf.processing_error or "pdf" in kf.processing_error or "startxref" in kf.processing_error


async def test_missing_object_marks_failed_with_error(session_maker, processing_settings: Settings) -> None:
    """5. Missing blob → ``failed`` + error message."""
    pdf = hello_pdf()
    fid = await _seed_knowledge_file(session_maker, pdf_bytes=pdf)

    async with session_maker() as session:
        svc = KnowledgeFileProcessingService(session, processing_settings, storage=_MissingObjectStorage())
        assert await svc.process_file(fid) == KnowledgeFileProcessingOutcome.FAILED

    async with session_maker() as session:
        kf = await session.get(KnowledgeFile, fid)
        assert kf is not None
        assert kf.processing_status == "failed"
        assert kf.processing_error
        assert "not found" in kf.processing_error.lower() or "Object" in kf.processing_error


async def test_unsupported_mime_marks_failed_with_error(session_maker, processing_settings: Settings) -> None:
    """5. Non-PDF mime → ``failed`` after claim."""
    pdf = hello_pdf()
    fid = await _seed_knowledge_file(session_maker, pdf_bytes=pdf, mime_type="application/octet-stream")
    storage = _MemoryStorage(pdf)

    async with session_maker() as session:
        svc = KnowledgeFileProcessingService(session, processing_settings, storage=storage)
        assert await svc.process_file(fid) == KnowledgeFileProcessingOutcome.FAILED

    async with session_maker() as session:
        kf = await session.get(KnowledgeFile, fid)
        assert kf is not None
        assert kf.processing_status == "failed"
        assert kf.processing_error
        assert "mime" in kf.processing_error.lower() or "application/octet-stream" in kf.processing_error


# --- Idempotency & safe rerun ---


async def test_second_process_skipped_when_already_ready(
    session_maker,
    processing_settings: Settings,
) -> None:
    pdf = hello_pdf()
    fid = await _seed_knowledge_file(session_maker, pdf_bytes=pdf)
    storage = _MemoryStorage(pdf)

    async with session_maker() as session:
        svc = KnowledgeFileProcessingService(session, processing_settings, storage=storage)
        assert await svc.process_file(fid) == KnowledgeFileProcessingOutcome.READY

    async with session_maker() as session:
        svc = KnowledgeFileProcessingService(session, processing_settings, storage=storage)
        assert await svc.process_file(fid) == KnowledgeFileProcessingOutcome.SKIPPED


async def test_retry_after_failed_reaches_ready_with_chunks(session_maker, processing_settings: Settings) -> None:
    """6. After ``failed``, a second run with valid PDF yields ``ready`` and chunks."""
    bad = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    good = hello_pdf()
    fid = await _seed_knowledge_file(session_maker, pdf_bytes=bad)

    async with session_maker() as session:
        svc = KnowledgeFileProcessingService(session, processing_settings, storage=_MemoryStorage(bad))
        assert await svc.process_file(fid) == KnowledgeFileProcessingOutcome.FAILED

    async with session_maker() as session:
        svc = KnowledgeFileProcessingService(session, processing_settings, storage=_MemoryStorage(good))
        assert await svc.process_file(fid) == KnowledgeFileProcessingOutcome.READY

    async with session_maker() as session:
        kf = await session.get(KnowledgeFile, fid)
        assert kf is not None
        assert kf.processing_status == "ready"
        assert kf.page_count == 1
        res = await session.execute(select(KnowledgeChunk).where(KnowledgeChunk.knowledge_file_id == fid))
        assert len(list(res.scalars().all())) >= 1


async def test_retry_after_ready_forced_to_failed_replaces_chunks(session_maker, processing_settings: Settings) -> None:
    """6. Simulate repair: row set back to ``failed`` → reprocess replaces chunk set."""
    pdf = hello_pdf()
    fid = await _seed_knowledge_file(session_maker, pdf_bytes=pdf)
    storage = _MemoryStorage(pdf)

    async with session_maker() as session:
        svc = KnowledgeFileProcessingService(session, processing_settings, storage=storage)
        assert await svc.process_file(fid) == KnowledgeFileProcessingOutcome.READY

    async with session_maker() as session:
        res = await session.execute(select(KnowledgeChunk).where(KnowledgeChunk.knowledge_file_id == fid))
        first_ids = {c.id for c in res.scalars().all()}
        assert first_ids

        await session.execute(
            update(KnowledgeFile)
            .where(KnowledgeFile.id == fid)
            .values(
                processing_status="failed",
                processing_error="simulated repair",
                page_count=None,
            ),
        )
        await session.commit()

    async with session_maker() as session:
        svc = KnowledgeFileProcessingService(session, processing_settings, storage=storage)
        assert await svc.process_file(fid) == KnowledgeFileProcessingOutcome.READY

    async with session_maker() as session:
        res = await session.execute(select(KnowledgeChunk).where(KnowledgeChunk.knowledge_file_id == fid))
        second_ids = {c.id for c in res.scalars().all()}
        assert second_ids
        assert second_ids.isdisjoint(first_ids), "chunks should be replaced (new row ids)"


async def test_process_skipped_unknown_file_id(session_maker, processing_settings: Settings) -> None:
    async with session_maker() as session:
        svc = KnowledgeFileProcessingService(session, processing_settings, storage=_MemoryStorage(b"x"))
        assert await svc.process_file(uuid.uuid4()) == KnowledgeFileProcessingOutcome.SKIPPED
