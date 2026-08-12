# Knowledge PDF ingestion (async queue)

## Overview

Uploading a PDF via `POST /api/v1/bots/{bot_id}/knowledge/files` **stores the blob in object storage**, inserts a `knowledge_files` row with `processing_status = uploaded`, and **enqueues** a Redis job containing only `file_id`.

Heavy work runs in a **separate worker process** (same codebase):

1. **Extract** text from the PDF (CPU-bound; offloaded with `asyncio.to_thread`).
2. **Chunk** text per `app.services.knowledge_text_chunking`.
3. **Persist** rows in `knowledge_chunks` and set `processing_status = ready`.

There is **no separate vector-embedding stage** in the current MVP: retrieval uses PostgreSQL full-text search on chunk text. A future embedding index would slot in after chunking as an additional worker step.

Full-text retrieval (`POST .../knowledge/retrieve`) joins chunks to files with `processing_status = 'ready'` only, so content is **not searchable** until the job completes.

## Components

| Piece | Role |
|-------|------|
| `app.core.knowledge_ingestion_queue` | Redis list queue (`LPUSH` / `BRPOP`), enqueue helper |
| `app.core.knowledge_ingestion_pipeline` | After each run: retry via re-enqueue or `dead_letter` |
| `app.workers.knowledge_ingestion_worker` | Long-running BRPOP loop |
| `app.services.knowledge_file_processing_service` | Claim row, read storage, extract, chunk, commit |
| `knowledge_files.ingestion_failure_count` | Counts failed attempts for retry / dead-letter |

## Configuration (`APP_` prefix)

| Variable | Notes |
|----------|--------|
| `APP_KNOWLEDGE_INGESTION_ENABLED` | Default `true`; if `false`, no enqueue after upload |
| `APP_KNOWLEDGE_INGESTION_REDIS_URL` | Optional; falls back to `APP_RATE_LIMIT_REDIS_URL` / `REDIS_URL` |
| `APP_KNOWLEDGE_INGESTION_QUEUE_KEY` | Redis list key (default `bf:knowledge:ingestion`) |
| `APP_KNOWLEDGE_INGESTION_MAX_ATTEMPTS` | Failures before `dead_letter` (no auto re-queue) |
| `APP_KNOWLEDGE_INGESTION_WORKER_BRPOP_TIMEOUT_SECONDS` | Blocking pop timeout (worker loop) |

If Redis is unavailable at upload time, the API **still returns 201**; enqueue errors are logged (`knowledge_ingestion_enqueue_failed`). Operators should monitor `uploaded` files stuck without workers.

## Observability

Structured logs (structlog) use events such as:

- `knowledge_ingestion_enqueued`
- `knowledge_ingestion_metric` with `event` = `completed` | `retry_scheduled` | `dead_letter` | `skipped`
- `knowledge_ingestion_worker_started` / `knowledge_ingestion_worker_misconfigured`

## API: job status

`GET /api/v1/bots/{bot_id}/knowledge/files/{file_id}/ingestion` returns a normalized lifecycle:

- `pending` (`uploaded`), `processing`, `completed` (`ready`), `failed`, `dead_letter`
- `searchable`: `true` only when `processing_status` is `ready`

## Docker Compose

Service **`knowledge-worker`** runs `python -m app.workers.knowledge_ingestion_worker` with the same image and `.env` as `backend`, depending on Postgres, Redis, and MinIO.
