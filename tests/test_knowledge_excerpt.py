"""Unit tests for :mod:`app.prompting.knowledge_excerpt`."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.prompting.knowledge_excerpt import format_knowledge_context_excerpt


def test_format_knowledge_context_excerpt_empty() -> None:
    assert format_knowledge_context_excerpt([]) == ""


def test_format_knowledge_context_excerpt_numbered_and_page() -> None:
    cid = uuid.uuid4()
    lines = format_knowledge_context_excerpt(
        [
            SimpleNamespace(
                chunk_id=cid,
                content="  Alpha fact.  ",
                original_filename="doc.txt",
                page_number=3,
            ),
        ],
    )
    assert "uploaded knowledge files" in lines
    assert "doc.txt" in lines
    assert "page 3" in lines
    assert f"id={cid}" in lines
    assert "Alpha fact." in lines
    assert "[1]" in lines


def test_format_knowledge_context_excerpt_omits_page_when_none() -> None:
    lines = format_knowledge_context_excerpt(
        [
            SimpleNamespace(
                chunk_id=uuid.uuid4(),
                content="x",
                original_filename="n.txt",
                page_number=None,
            ),
        ],
    )
    assert ", page " not in lines
    assert "n.txt" in lines
