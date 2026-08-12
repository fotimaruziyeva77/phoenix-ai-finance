"""
Format budgeted knowledge chunks into a single system-prompt section.

Provider-agnostic and PDF-agnostic: only uses generic citation fields on each item.
"""

from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable


@runtime_checkable
class _KnowledgeContextLine(Protocol):
    chunk_id: Any
    content: str
    original_filename: str
    page_number: int | None


def format_knowledge_context_excerpt(items: Sequence[_KnowledgeContextLine]) -> str:
    """
    Build one system-prompt block the model can cite; ordered as given (relevance order).

    Callers must pass already budget-selected items (e.g. from context selection).
    """
    if not items:
        return ""

    header = (
        "The following excerpts are from the bot owner's uploaded knowledge files. "
        "Use them only when they help answer the user's latest message; if they are irrelevant, ignore them. "
        "Do not invent facts not supported by these excerpts.\n"
    )
    blocks: list[str] = [header]
    for i, it in enumerate(items, start=1):
        page = it.page_number
        page_part = f", page {page}" if page is not None else ""
        blocks.append(f"[{i}] Source: {it.original_filename}{page_part} (id={it.chunk_id})")
        blocks.append(it.content.strip())
        blocks.append("")
    return "\n".join(blocks).strip()
