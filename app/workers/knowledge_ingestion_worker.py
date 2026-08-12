"""
Standalone process: BRPOP knowledge ingestion queue, run PDF pipeline, handle retries / dead-letter.

Run (Docker / prod): ``python -m app.workers.knowledge_ingestion_worker``

Requires ``APP_KNOWLEDGE_INGESTION_*`` / Redis URL (see :class:`~app.core.config.Settings`).
"""

from __future__ import annotations

import asyncio
import sys

from app.core.config import get_settings
from app.core.db import dispose_engine
from app.core.error_tracking import init_error_tracking
from app.core.knowledge_ingestion_pipeline import handle_knowledge_processing_outcome
from app.core.knowledge_ingestion_queue import knowledge_ingestion_queue_from_settings
from app.core.logging import configure_logging, get_logger
from app.workers.knowledge_pdf_processing import process_knowledge_file_standalone

_LOG = get_logger("knowledge_ingestion_worker")


async def _run_loop() -> None:
    settings = get_settings()
    configure_logging(
        log_level=settings.log_level,
        json_logs=settings.log_json,
        service_name=f"{settings.service_name}-knowledge-worker",
        environment=settings.environment,
        suppress_uvicorn_access=True,
    )
    init_error_tracking(settings)
    queue = await knowledge_ingestion_queue_from_settings(settings)
    if queue is None:
        _LOG.error(
            "knowledge_ingestion_worker_misconfigured",
            reason="queue_unavailable",
            hint="Set Redis URL (APP_RATE_LIMIT_REDIS_URL or APP_KNOWLEDGE_INGESTION_REDIS_URL) "
            "and APP_KNOWLEDGE_INGESTION_ENABLED=true.",
        )
        sys.exit(2)

    timeout = settings.knowledge_ingestion_worker_brpop_timeout_seconds
    _LOG.info(
        "knowledge_ingestion_worker_started",
        queue_key=settings.knowledge_ingestion_queue_key,
        brpop_timeout_seconds=timeout,
        max_attempts=settings.knowledge_ingestion_max_attempts,
    )

    try:
        while True:
            file_id = await queue.blocking_pop_next(timeout_seconds=timeout)
            if file_id is None:
                continue
            try:
                outcome = await process_knowledge_file_standalone(file_id)
                await handle_knowledge_processing_outcome(
                    file_id,
                    outcome,
                    settings=settings,
                    queue=queue,
                )
            except Exception as exc:  # noqa: BLE001 — keep worker alive
                _LOG.exception(
                    "knowledge_ingestion_worker_iteration_failed",
                    file_id=str(file_id),
                    error=str(exc),
                )
    finally:
        await dispose_engine()


def main() -> None:
    try:
        asyncio.run(_run_loop())
    except KeyboardInterrupt:
        _LOG.info("knowledge_ingestion_worker_stopped", reason="keyboard_interrupt")


if __name__ == "__main__":
    main()
