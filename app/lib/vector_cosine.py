"""Pure-Python cosine similarity for small embedding vectors (semantic cache)."""

from __future__ import annotations

from collections.abc import Sequence


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Return cosine similarity in ``[0, 1]`` for non-negative typical embeddings; 0.0 on degenerate input."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=True):
        dot += float(x) * float(y)
        na += float(x) * float(x)
        nb += float(y) * float(y)
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    v = dot / (na**0.5 * nb**0.5)
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return float(v)


__all__ = ["cosine_similarity"]
