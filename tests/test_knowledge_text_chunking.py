"""Unit tests for :mod:`app.services.knowledge_text_chunking`.

Covers stable ordering, sensible splits for large text, minimal fragmentation for short text,
``page_number`` preservation, and ``token_count`` / text edge cases.
"""

from __future__ import annotations

import pytest
from app.services.knowledge_text_chunking import (
    build_chunk_specs_from_pages,
    chunk_page_text,
    estimate_token_count,
)


def test_estimate_token_count_empty() -> None:
    assert estimate_token_count("", chars_per_token=4.0) == 0
    assert estimate_token_count("   ", chars_per_token=4.0) == 0


def test_estimate_token_count_rounds_up() -> None:
    assert estimate_token_count("abcd", chars_per_token=4.0) == 1
    assert estimate_token_count("abcde", chars_per_token=4.0) == 2


def test_build_chunk_specs_skips_empty_pages() -> None:
    assert build_chunk_specs_from_pages([(1, ""), (2, "   ")], max_chars=100, chars_per_token_estimate=4.0) == []


def test_build_chunk_specs_single_page() -> None:
    specs = build_chunk_specs_from_pages(
        [(1, "Hello world")],
        max_chars=100,
        chars_per_token_estimate=4.0,
    )
    assert len(specs) == 1
    assert specs[0].page_number == 1
    assert specs[0].content == "Hello world"
    assert specs[0].token_count == 3  # ceil(11/4)


def test_build_chunk_specs_merges_paragraphs_when_under_cap() -> None:
    specs = build_chunk_specs_from_pages(
        [(1, "First para.\n\nSecond para.")],
        max_chars=100,
        chars_per_token_estimate=10.0,
    )
    assert len(specs) == 1
    assert specs[0].content == "First para.\n\nSecond para."
    assert specs[0].page_number == 1


def test_build_chunk_specs_splits_paragraphs_when_over_cap() -> None:
    specs = build_chunk_specs_from_pages(
        [(1, "AA\n\nBB")],
        max_chars=2,
        chars_per_token_estimate=10.0,
    )
    assert len(specs) == 2
    assert specs[0].content == "AA"
    assert specs[1].content == "BB"


def test_build_chunk_specs_splits_long_page() -> None:
    long = "a" * 250
    specs = build_chunk_specs_from_pages([(1, long)], max_chars=100, chars_per_token_estimate=10.0)
    assert len(specs) >= 2
    assert all(s.page_number == 1 for s in specs)
    joined = "".join(s.content for s in specs)
    assert joined.replace(" ", "") == long


def test_line_packing_for_single_block_with_newlines() -> None:
    """Dense PDF-style text: no blank lines, multiple single-newline rows."""
    specs = chunk_page_text(
        "alpha\nbeta\ngamma",
        page_number=2,
        max_chars=12,
        chars_per_token_estimate=4.0,
    )
    assert len(specs) >= 1
    assert all(s.page_number == 2 for s in specs)
    assert "alpha" in specs[0].content
    joined = "\n".join(s.content for s in specs)
    assert "alpha" in joined and "beta" in joined and "gamma" in joined


def test_multi_page_order_preserved() -> None:
    specs = build_chunk_specs_from_pages(
        [(1, "P1"), (2, "P2a\n\nP2b")],
        max_chars=5,
        chars_per_token_estimate=4.0,
    )
    pages = [s.page_number for s in specs]
    assert pages == [1, 2, 2]
    assert specs[0].content == "P1"
    assert specs[1].content == "P2a"
    assert specs[2].content == "P2b"


def test_deterministic_same_input_same_output() -> None:
    pages = [(1, "A\n\nB\n\nC"), (2, "x" * 80)]
    a = build_chunk_specs_from_pages(pages, max_chars=30, chars_per_token_estimate=4.0)
    b = build_chunk_specs_from_pages(pages, max_chars=30, chars_per_token_estimate=4.0)
    assert a == b


# --- 1. Stable order (page order, then within-page emission order) ---


def test_chunks_emitted_in_stable_sequence_across_pages() -> None:
    specs = build_chunk_specs_from_pages(
        [(1, "a"), (2, "b"), (3, "c")],
        max_chars=100,
        chars_per_token_estimate=4.0,
    )
    assert [s.content for s in specs] == ["a", "b", "c"]
    assert [s.page_number for s in specs] == [1, 2, 3]


def test_within_page_order_matches_source_paragraph_order() -> None:
    specs = build_chunk_specs_from_pages(
        [(1, "zebra\n\napple\n\nmango")],
        max_chars=8,
        chars_per_token_estimate=4.0,
    )
    assert [s.content for s in specs] == ["zebra", "apple", "mango"]


# --- 2. Large text splits sensibly (prefer newline when in window) ---


def test_long_unbroken_line_splits_at_max_chars_without_dropping_chars() -> None:
    long = "z" * 300
    specs = build_chunk_specs_from_pages([(1, long)], max_chars=100, chars_per_token_estimate=10.0)
    assert len(specs) == 3
    assert all(len(s.content) <= 100 for s in specs)
    assert "".join(s.content for s in specs) == long


def test_long_text_prefers_split_at_newline_when_reasonable() -> None:
    """First window should break at the single newline (in second half of window)."""
    left, right = "x" * 30, "y" * 30
    text = left + "\n" + right
    specs = build_chunk_specs_from_pages([(1, text)], max_chars=50, chars_per_token_estimate=10.0)
    assert len(specs) == 2
    assert specs[0].content == left
    assert specs[1].content == right


def test_line_packed_page_respects_order_when_splitting() -> None:
    """Many lines: merged where possible, order preserved."""
    lines = [f"line{i}" for i in range(5)]
    text = "\n".join(lines)
    specs = chunk_page_text(text, page_number=1, max_chars=20, chars_per_token_estimate=4.0)
    flattened = []
    for s in specs:
        flattened.extend(s.content.split("\n"))
    assert flattened == lines


# --- 3. Short text does not over-fragment ---


def test_single_short_sentence_stays_one_chunk() -> None:
    specs = build_chunk_specs_from_pages(
        [(1, "OK.")],
        max_chars=4000,
        chars_per_token_estimate=4.0,
    )
    assert len(specs) == 1
    assert specs[0].content == "OK."


def test_many_short_paragraphs_merge_when_under_cap() -> None:
    body = "\n\n".join([f"p{i}" for i in range(10)])
    specs = build_chunk_specs_from_pages([(1, body)], max_chars=500, chars_per_token_estimate=4.0)
    assert len(specs) == 1
    assert body == specs[0].content


def test_short_lines_merge_into_few_chunks() -> None:
    text = "\n".join(["a", "b", "c", "d"])
    specs = chunk_page_text(text, page_number=1, max_chars=100, chars_per_token_estimate=4.0)
    assert len(specs) == 1
    assert specs[0].content == text


# --- 4. Page number preserved ---


def test_every_chunk_carries_correct_page_number_multi_page() -> None:
    specs = build_chunk_specs_from_pages(
        [(10, "one"), (11, "two\n\nthree")],
        max_chars=5,
        chars_per_token_estimate=4.0,
    )
    assert [(s.page_number, s.content) for s in specs] == [
        (10, "one"),
        (11, "two"),
        (11, "three"),
    ]


def test_page_number_preserved_when_text_hard_split_exceeds_max_chars() -> None:
    """Every fragment from the same page keeps that ``page_number``."""
    specs = build_chunk_specs_from_pages(
        [(7, "three")],
        max_chars=4,
        chars_per_token_estimate=4.0,
    )
    assert len(specs) == 2
    assert all(s.page_number == 7 for s in specs)
    assert specs[0].content + specs[1].content == "three"


# --- 5. token_count hook ---


def test_token_count_matches_ceil_len_over_estimate() -> None:
    specs = build_chunk_specs_from_pages(
        [(1, "Hello")],
        max_chars=100,
        chars_per_token_estimate=4.0,
    )
    assert specs[0].token_count == estimate_token_count("Hello", chars_per_token=4.0)
    assert specs[0].token_count == 2  # ceil(5/4)


def test_token_count_per_chunk_independent() -> None:
    specs = build_chunk_specs_from_pages(
        [(1, "AA\n\nBBBB")],
        max_chars=3,
        chars_per_token_estimate=2.0,
    )
    assert specs[0].token_count == estimate_token_count("AA", chars_per_token=2.0)
    assert specs[1].token_count == estimate_token_count("BBBB", chars_per_token=2.0)


# --- Text edge cases ---


def test_rejects_non_positive_max_chars() -> None:
    with pytest.raises(ValueError, match="max_chars"):
        build_chunk_specs_from_pages([(1, "x")], max_chars=0, chars_per_token_estimate=4.0)


def test_rejects_non_positive_chars_per_token() -> None:
    with pytest.raises(ValueError, match="chars_per_token_estimate"):
        build_chunk_specs_from_pages([(1, "x")], max_chars=10, chars_per_token_estimate=0.0)


def test_estimate_token_count_rejects_non_positive_divisor() -> None:
    with pytest.raises(ValueError, match="chars_per_token"):
        estimate_token_count("a", chars_per_token=0.0)


def test_triple_blank_lines_treated_as_single_paragraph_boundary() -> None:
    specs = build_chunk_specs_from_pages(
        [(1, "A\n\n\n\nB")],
        max_chars=100,
        chars_per_token_estimate=4.0,
    )
    assert len(specs) == 1
    assert specs[0].content == "A\n\nB"


def test_crlf_paragraph_boundary() -> None:
    specs = build_chunk_specs_from_pages(
        [(1, "First\r\n\r\nSecond")],
        max_chars=100,
        chars_per_token_estimate=4.0,
    )
    assert len(specs) == 1
    assert "First" in specs[0].content and "Second" in specs[0].content


def test_unicode_grapheme_length_uses_python_str_len() -> None:
    text = "café " * 20  # 5 chars * 20 = 100, space included in "café "
    specs = build_chunk_specs_from_pages([(1, text.strip())], max_chars=100, chars_per_token_estimate=5.0)
    assert len(specs) >= 1
    joined = " ".join(s.content for s in specs) if len(specs) > 1 else specs[0].content
    assert "café" in joined


def test_leading_trailing_whitespace_stripped_on_page() -> None:
    specs = build_chunk_specs_from_pages(
        [(1, "  \n\n  inner  \n\n  ")],
        max_chars=100,
        chars_per_token_estimate=4.0,
    )
    assert len(specs) == 1
    assert specs[0].content == "inner"


def test_only_newlines_yields_no_chunks() -> None:
    assert build_chunk_specs_from_pages([(1, "\n\n\n")], max_chars=100, chars_per_token_estimate=4.0) == []


def test_chunk_page_text_explicit_page_number() -> None:
    specs = chunk_page_text("solo", page_number=99, max_chars=10, chars_per_token_estimate=4.0)
    assert len(specs) == 1
    assert specs[0].page_number == 99
