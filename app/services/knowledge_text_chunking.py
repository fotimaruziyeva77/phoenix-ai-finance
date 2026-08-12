"""
Retrieval-oriented chunking for extracted PDF text (no tokenizers, no embeddings).

Strategy (MVP hybrid)
---------------------
1. **Paragraph-first**: split on blank lines (``\\n\\n``). Pack consecutive paragraphs into one
   chunk until adding the next would exceed ``max_chars``, joining with ``\\n\\n`` so structure
   stays readable.
2. **Line packing fallback**: when a page is effectively one block (common for pypdf output),
   split on single newlines and pack lines with ``\\n`` until ``max_chars``.
3. **Length cap**: any unit still longer than ``max_chars`` is split hard, preferring newline
   boundaries inside the window (deterministic).

**Why hybrid:** PDF extractors rarely emit true paragraphs; paragraph-only chunking would often
yield one huge chunk per page. Pure length-only splits mid-sentence and hurts readability.
Combining paragraph boundaries, then line boundaries, then a fixed char cap gives ordered,
stable chunks that map cleanly to ``page_number`` and support future **cost-aware retrieval**
via ``token_count`` estimates (replace :func:`estimate_token_count` with a real tokenizer later).
"""

from __future__ import annotations

import math
import re
from typing import NamedTuple

# Blank-line paragraph boundary (handles \\r\\n and multiple blank lines).
_PARA_SPLIT = re.compile(r"\r?\n\s*\r?\n+")

# Number of chars copied from the tail of chunk N to the head of chunk N+1.
_OVERLAP_CHARS: int = 100


class ChunkSpec(NamedTuple):
    """Ordered chunk to persist; ``chunk_index`` is assigned by the repository in page order."""

    page_number: int | None
    content: str
    token_count: int | None


def _has_cjk(text: str) -> bool:
    """Return True if the first 200 characters of *text* contain any CJK codepoint."""
    return any(
        '\u4e00' <= ch <= '\u9fff' or '\u3040' <= ch <= '\u30ff'
        for ch in text[:200]
    )


def estimate_token_count(text: str, *, chars_per_token: float) -> int:
    """
    MVP token estimate for budgeting / future cost-aware retrieval.

    For CJK-heavy text, a lower ``chars_per_token`` (max 1.5) is used automatically
    because CJK characters are typically one token each.

    Replace with provider tokenizer counts or tiktoken when you wire real usage billing.
    """
    if chars_per_token <= 0:
        raise ValueError("chars_per_token must be positive")
    t = (text or "").strip()
    if not t:
        return 0
    if _has_cjk(t):
        chars_per_token = min(chars_per_token, 1.5)
    return max(1, int(math.ceil(len(t) / chars_per_token)))


def _split_paragraphs(page_text: str) -> list[str]:
    parts = _PARA_SPLIT.split((page_text or "").strip())
    return [p.strip() for p in parts if p.strip()]


def _split_lines(block: str) -> list[str]:
    return [ln.strip() for ln in (block or "").splitlines() if ln.strip()]


def _split_oversized_unit(text: str, max_chars: int) -> list[str]:
    """Hard split of a single unit into segments <= max_chars; prefer newline breaks."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    parts: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        chunk = text[start:end]
        if end < n:
            nl = chunk.rfind("\n")
            if nl > max(max_chars // 2, 1):
                chunk = chunk[:nl]
                end = start + nl
                if not chunk.strip():
                    end = start + max_chars
                    chunk = text[start:end]
        piece = chunk.strip()
        if piece:
            parts.append(piece)
        start = end if end > start else start + max_chars
    return parts


def _pack_units(
    units: list[str],
    *,
    max_chars: int,
    separator: str,
) -> list[str]:
    """
    Greedily merge consecutive units without reordering; each output string is <= max_chars
    (except units longer than max_chars are split first).
    """
    if max_chars < 1:
        raise ValueError("max_chars must be positive")

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    sep_len = len(separator)

    for raw in units:
        u = raw.strip()
        if not u:
            continue

        if len(u) > max_chars:
            if current:
                chunks.append(separator.join(current))
                current = []
                current_len = 0
            chunks.extend(_split_oversized_unit(u, max_chars))
            continue

        extra = sep_len + len(u) if current else len(u)
        if current_len + extra > max_chars:
            chunks.append(separator.join(current))
            current = [u]
            current_len = len(u)
        else:
            current.append(u)
            current_len += extra

    if current:
        chunks.append(separator.join(current))
    return chunks


def chunk_page_text(
    page_text: str,
    *,
    page_number: int,
    max_chars: int,
    chars_per_token_estimate: float,
) -> list[ChunkSpec]:
    """
    Split one page's text into ordered :class:`ChunkSpec` rows (same ``page_number`` on each).
    """
    page_text = (page_text or "").strip()
    if not page_text:
        return []

    paragraphs = _split_paragraphs(page_text)

    if len(paragraphs) == 1 and len(paragraphs[0]) > max_chars:
        lines = _split_lines(paragraphs[0])
        if len(lines) > 1:
            packed = _pack_units(lines, max_chars=max_chars, separator="\n")
        else:
            packed = _split_oversized_unit(paragraphs[0], max_chars)
    elif not paragraphs:
        return []
    else:
        packed = _pack_units(paragraphs, max_chars=max_chars, separator="\n\n")

    return [
        ChunkSpec(
            page_number=page_number,
            content=segment,
            token_count=estimate_token_count(segment, chars_per_token=chars_per_token_estimate),
        )
        for segment in packed
        if segment.strip()
    ]


def _apply_overlap(specs: list[ChunkSpec], overlap_chars: int) -> list[ChunkSpec]:
    """
    Copy the last ``overlap_chars`` characters of chunk *N* to the beginning of chunk *N+1*.

    This prevents context loss at chunk boundaries without changing page attribution.
    Token counts are recomputed after the prefix is prepended.
    """
    if overlap_chars <= 0 or len(specs) < 2:
        return specs

    result: list[ChunkSpec] = [specs[0]]
    for i in range(1, len(specs)):
        prev_content = specs[i - 1].content
        tail = prev_content[-overlap_chars:].strip()
        current = specs[i]
        if tail:
            new_content = tail + "\n" + current.content
            # Recompute token count using the same ratio derived from original estimate.
            orig_len = len(current.content)
            if current.token_count and orig_len > 0:
                ratio = current.token_count / orig_len
                new_token_count = max(1, int(math.ceil(len(new_content) * ratio)))
            else:
                new_token_count = current.token_count
            result.append(ChunkSpec(
                page_number=current.page_number,
                content=new_content,
                token_count=new_token_count,
            ))
        else:
            result.append(current)
    return result


def build_chunk_specs_from_pages(
    pages: list[tuple[int, str]],
    *,
    max_chars: int,
    chars_per_token_estimate: float,
    overlap_chars: int = _OVERLAP_CHARS,
) -> list[ChunkSpec]:
    """
    Build ordered chunk specs across pages (page order, then chunk order within page).

    ``page_number`` is 1-based, aligned with PDF extraction.

    ``overlap_chars`` characters from the tail of each chunk are prepended to the next
    chunk to preserve context across boundaries (default: ``_OVERLAP_CHARS``).
    """
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    if chars_per_token_estimate <= 0:
        raise ValueError("chars_per_token_estimate must be positive")

    specs: list[ChunkSpec] = []
    for page_number, text in pages:
        specs.extend(
            chunk_page_text(
                text,
                page_number=page_number,
                max_chars=max_chars,
                chars_per_token_estimate=chars_per_token_estimate,
            )
        )
    return _apply_overlap(specs, overlap_chars)
