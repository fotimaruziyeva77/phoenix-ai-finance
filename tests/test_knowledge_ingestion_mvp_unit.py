"""Fast unit checks for knowledge ingestion MVP data model (no database)."""

from __future__ import annotations

from app.models.knowledge_chunk import KnowledgeChunk


def test_vector_embeddings_not_persisted_mvp_documents_fts_surface() -> None:
    """MVP stores chunk text only; retrieval uses PostgreSQL FTS, not a vector embedding column."""
    assert "embedding" not in KnowledgeChunk.__table__.columns.keys()
