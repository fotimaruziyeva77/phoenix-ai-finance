"""Unit tests for :mod:`app.services.knowledge_pdf_text_extraction`."""

from __future__ import annotations

import pytest
from app.services.knowledge_pdf_text_extraction import extract_pdf_text_by_page

from tests.fixtures.knowledge_pdf_samples import hello_pdf


def test_extract_empty_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        extract_pdf_text_by_page(b"")


def test_extract_invalid_raises() -> None:
    with pytest.raises(ValueError, match="Invalid|unreadable"):
        extract_pdf_text_by_page(b"not a pdf")


def test_extract_hello_pdf() -> None:
    n, pages = extract_pdf_text_by_page(hello_pdf())
    assert n == 1
    assert len(pages) == 1
    assert pages[0][0] == 1
    assert "Hello" in pages[0][1]


def test_extract_two_page_sample() -> None:
    from tests.fixtures.knowledge_pdf_samples import two_page_hello_pdf

    n, pages = extract_pdf_text_by_page(two_page_hello_pdf())
    assert n == 2
    assert len(pages) == 2
    assert pages[0][0] == 1 and pages[1][0] == 2
    assert any("Hello" in t for _, t in pages)
