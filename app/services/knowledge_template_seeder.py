"""
Seed a newly created bot's knowledge base with niche-specific FAQ templates.

Called during ``BotService.create_bot_for_user()`` — creates a synthetic
``KnowledgeFile`` (no S3 blob) with ``processing_status='ready'`` and
immediately inserts ``KnowledgeChunk`` rows so the content is searchable
without going through the async ingestion worker.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.niche_knowledge_templates import KBTemplate, get_knowledge_templates
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_file import KnowledgeFile
from app.services.knowledge_text_chunking import estimate_token_count

# Synthetic file metadata for niche FAQ templates.
_TEMPLATE_FILENAME = "niche-faq-template.txt"
_TEMPLATE_MIME = "text/plain"
_CHARS_PER_TOKEN_EST = 4.0


def _chunk_content(tmpl: KBTemplate) -> str:
    """Format a single FAQ entry as searchable text."""
    return f"Q: {tmpl.question}\nA: {tmpl.answer}"


async def seed_knowledge_templates(
    session: AsyncSession,
    *,
    bot_id: uuid.UUID,
    owner_id: uuid.UUID,
    niche_id: str,
) -> uuid.UUID | None:
    """Create a template knowledge file with FAQ chunks for *niche_id*.

    Returns the ``KnowledgeFile.id`` if templates were seeded, ``None`` otherwise
    (e.g. unknown niche or no templates configured).

    Uses the caller's *session* — does **not** commit; the caller controls the
    transaction boundary.
    """
    templates = get_knowledge_templates(niche_id)
    if not templates:
        return None

    file_id = uuid.uuid4()
    storage_key = f"_template/{bot_id}/{file_id}/niche-faq.txt"

    # Compute synthetic file size (sum of all chunk content).
    chunks_text = [_chunk_content(t) for t in templates]
    total_bytes = sum(len(c.encode("utf-8")) for c in chunks_text)

    # 1. Create synthetic KnowledgeFile — already "ready" (no worker needed).
    file_row = KnowledgeFile(
        id=file_id,
        bot_id=bot_id,
        owner_id=owner_id,
        original_filename=_TEMPLATE_FILENAME,
        storage_key=storage_key,
        mime_type=_TEMPLATE_MIME,
        file_size_bytes=total_bytes,
        processing_status="ready",
        page_count=1,
    )
    session.add(file_row)

    # 2. Create KnowledgeChunk rows — one per FAQ entry.
    chunk_rows: list[KnowledgeChunk] = []
    for idx, content in enumerate(chunks_text):
        chunk_rows.append(
            KnowledgeChunk(
                knowledge_file_id=file_id,
                bot_id=bot_id,
                owner_id=owner_id,
                chunk_index=idx,
                page_number=1,
                content=content,
                token_count=estimate_token_count(content, chars_per_token=_CHARS_PER_TOKEN_EST),
            )
        )
    session.add_all(chunk_rows)
    await session.flush()

    return file_id
