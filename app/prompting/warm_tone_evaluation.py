"""
Lightweight **heuristic checks** for assistant replies expected under warm-tone prompting.

Use in tests, golden datasets, or offline linting—not as a substitute for human review.
"""

from __future__ import annotations

import re

# Phrases we explicitly tell the model to avoid; catches obvious regressions in samples/tests.
_ROBOTIC_SUBSTRINGS: tuple[str, ...] = (
    "as an ai",
    "as a language model",
    "i'm an ai",
    "i am an ai",
    "i'm a language model",
    "ai language model",
    "i cannot help",
    "i do not have the ability",
)

# Checklist / dump patterns (robotic sales bots).
_CHECKLIST_MARKERS: tuple[str, ...] = (
    "\n- ",
    "\n* ",
    "\n1.",
    "\n2.",
)


def count_question_marks(text: str) -> int:
    return text.count("?")


def rough_sentence_count(text: str) -> int:
    """Split on sentence boundaries; ignores empty segments."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return len([p for p in parts if p.strip()])


def evaluate_warm_tone_response(
    text: str,
    *,
    max_chars: int = 800,
    max_sentences: int = 5,
    max_question_marks: int = 1,
    expect_at_least_one_question: bool = False,
) -> tuple[bool, tuple[str, ...]]:
    """
    Return ``(ok, violations)`` for a single assistant message.

    * **Concise** — character cap + sentence cap.
    * **One question** — at most ``max_question_marks`` (default one).
    * **Human-like / not robotic** — banned boilerplate substrings; no markdown checklist dumps.
    """
    violations: list[str] = []
    raw = text.strip()
    if not raw:
        return False, ("empty",)

    lower = raw.lower()
    if len(raw) > max_chars:
        violations.append(f"too_long_chars>{max_chars}")

    sc = rough_sentence_count(raw)
    if sc > max_sentences:
        violations.append(f"too_many_sentences>{max_sentences}")

    q = count_question_marks(raw)
    if q > max_question_marks:
        violations.append(f"too_many_questions>{max_question_marks}")
    if expect_at_least_one_question and q < 1:
        violations.append("expected_question_missing")

    for bad in _ROBOTIC_SUBSTRINGS:
        if bad in lower:
            violations.append(f"robotic_phrase:{bad}")

    for marker in _CHECKLIST_MARKERS:
        if marker in raw:
            violations.append(f"checklist_dump:{marker.strip()}")

    if "\n\n\n" in raw:
        violations.append("paragraph_stuffing")

    return (len(violations) == 0, tuple(violations))


__all__ = [
    "count_question_marks",
    "evaluate_warm_tone_response",
    "rough_sentence_count",
]
