"""Post-processing after :func:`~app.workers.knowledge_pdf_processing.process_knowledge_file_standalone` runs."""

from __future__ import annotations

import uuid

from app.core.config import Settings
from app.core.db import get_session_maker
from app.core.knowledge_ingestion_queue import RedisKnowledgeIngestionQueue
from app.core.logging import get_logger
from app.repositories.knowledge_file_repository import KnowledgeFileRepository
from app.services.knowledge_file_processing_service import KnowledgeFileProcessingOutcome
from app.workers.knowledge_pdf_processing import process_knowledge_file_standalone

_LOG = get_logger("knowledge_ingestion_pipeline")


async def handle_knowledge_processing_outcome(
    file_id: uuid.UUID,
    outcome: KnowledgeFileProcessingOutcome,
    *,
    settings: Settings,
    queue: RedisKnowledgeIngestionQueue,
) -> None:
    """
    Metrics, retries, and dead-letter after one processing attempt.

    * READY / SKIPPED: no retry bookkeeping.
    * FAILED: increment ``ingestion_failure_count``; re-enqueue unless max attempts reached,
      then set ``dead_letter``.
    """
    if outcome == KnowledgeFileProcessingOutcome.READY:
        _LOG.info(
            "knowledge_ingestion_metric",
            event="completed",
            file_id=str(file_id),
            outcome="ready",
        )
        return

    if outcome == KnowledgeFileProcessingOutcome.SKIPPED:
        _LOG.info(
            "knowledge_ingestion_metric",
            event="skipped",
            file_id=str(file_id),
            outcome="skipped",
        )
        return

    maker = get_session_maker()
    async with maker() as session:
        repo = KnowledgeFileRepository(session)
        n = await repo.increment_ingestion_failure_count(file_id)
        max_a = settings.knowledge_ingestion_max_attempts
        if n is None:
            await session.rollback()
            _LOG.warning(
                "knowledge_ingestion_failure_increment_miss",
                file_id=str(file_id),
            )
            return

        if n >= max_a:
            await repo.mark_processing_dead_letter(file_id)
            await session.commit()
            _LOG.warning(
                "knowledge_ingestion_metric",
                event="dead_letter",
                observability_signal="queue_dead_letter",
                file_id=str(file_id),
                failure_count=n,
                max_attempts=max_a,
            )
            return

        await session.commit()

    await queue.enqueue(file_id)
    _LOG.info(
        "knowledge_ingestion_metric",
        event="retry_scheduled",
        file_id=str(file_id),
        failure_count=n,
        max_attempts=max_a,
    )


async def dequeue_and_process_one(
    *,
    settings: Settings,
    queue: RedisKnowledgeIngestionQueue,
) -> bool:
    """
    Pop one message (non-blocking), run processing, apply retry/dead-letter policy.

    Intended for integration tests and operational one-off drains.
    """
    file_id = await queue.non_blocking_pop_next()
    if file_id is None:
        return False
    outcome = await process_knowledge_file_standalone(file_id)
    await handle_knowledge_processing_outcome(
        file_id,
        outcome,
        settings=settings,
        queue=queue,
    )
    return True
