"""
Worker-oriented entrypoints for knowledge PDF text extraction.

Design notes (worker-ready)
---------------------------
- **Synchronous dev/tests**: call :func:`process_knowledge_file_job` with an existing
  :class:`~sqlalchemy.ext.asyncio.AsyncSession` from FastAPI deps or a test fixture.
- **Background workers**: enqueue ``file_id`` only; the worker opens its own session
  (see :func:`process_knowledge_file_standalone`) and runs the same job function.
  No PDF parsing or storage I/O belongs in API route handlers.
- **Idempotency**: claiming uses ``UPDATE … WHERE status IN ('uploaded','failed')`` so only
  one worker processes a file; duplicate jobs see :attr:`~app.services.knowledge_file_processing_service.KnowledgeFileProcessingOutcome.SKIPPED`.
  Successful runs **replace** chunks (delete + insert) so retries after ``failed`` are safe.
- **Stuck ``processing``**: if a worker dies after claim, the row stays ``processing`` and
  will not be auto-picked without a future reconciliation job (TTL / manual reset to ``failed``).

Production path: the Redis-backed worker in :mod:`app.workers.knowledge_ingestion_worker`
BRPOPs ``file_id`` messages and calls :func:`process_knowledge_file_standalone`. The API enqueues
after each successful upload via :func:`app.core.knowledge_ingestion_queue.schedule_knowledge_file_ingestion`.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_session_maker
from app.services.knowledge_file_processing_service import (
    KnowledgeFileProcessingOutcome,
    KnowledgeFileProcessingService,
)


async def process_knowledge_file_job(
    session: AsyncSession,
    file_id: uuid.UUID,
    *,
    settings: Settings | None = None,
) -> KnowledgeFileProcessingOutcome:
    """
    Process a single knowledge file using the given session.

    Performs internal commits; the passed-in session may be left with no open transaction.
    """
    s = settings or get_settings()
    svc = KnowledgeFileProcessingService(session, s)
    return await svc.process_file(file_id)


async def process_knowledge_file_standalone(file_id: uuid.UUID) -> KnowledgeFileProcessingOutcome:
    """Open a new DB session and process ``file_id`` (intended for queue workers)."""
    maker = get_session_maker()
    async with maker() as session:
        return await process_knowledge_file_job(session, file_id, settings=get_settings())
