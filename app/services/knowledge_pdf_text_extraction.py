"""
Pure PDF text extraction (no OCR, no I/O).

Uses pypdf ``page.extract_text()`` only. Call from a thread when invoked from async code.
"""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


# Hard ceiling on pages parsed per document. Far above any realistic knowledge PDF, but bounds
# the per-page extract_text() work so a small-but-many-page file can't exhaust the worker.
_MAX_PAGES_HARD_CAP = 2000


def extract_pdf_text_by_page(
    pdf_bytes: bytes,
    *,
    max_pages: int = _MAX_PAGES_HARD_CAP,
) -> tuple[int, list[tuple[int, str]]]:
    """
    Extract plain text per page (up to ``max_pages``).

    Returns:
        ``(page_count, segments)`` where ``segments`` is
        ``(page_number_1based, text)`` for each page (empty string if no extractable text).
        ``page_count`` is the number of pages actually processed (capped at ``max_pages``).
    """
    if not pdf_bytes:
        raise ValueError("PDF payload is empty")

    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=False)
    except PdfReadError as exc:
        raise ValueError(f"Invalid or unreadable PDF: {exc}") from exc

    cap = max(1, int(max_pages))
    total_pages = len(reader.pages)
    page_count = min(total_pages, cap)
    out: list[tuple[int, str]] = []
    for idx in range(1, page_count + 1):
        raw = reader.pages[idx - 1].extract_text()
        text = (raw or "").strip()
        out.append((idx, text))
    return page_count, out
