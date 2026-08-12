from app.lib.vector_cosine import cosine_similarity


def test_cosine_identical_unit_vectors() -> None:
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert abs(cosine_similarity(a, b) - 1.0) < 1e-9


def test_cosine_orthogonal() -> None:
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert cosine_similarity(a, b) == 0.0


def test_cosine_mismatched_length() -> None:
    assert cosine_similarity([1.0], [1.0, 0.0]) == 0.0
