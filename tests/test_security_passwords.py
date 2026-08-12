"""
Unit tests: password hashing (Argon2id).

Checklist
---------
1. Hash output is never the raw password (see ``test_password_hash_is_not_plaintext``).
2. ``verify_password`` accepts the correct secret and rejects wrong ones.

Edge cases (brief)
------------------
* **Empty password**: ``hash_password`` raises; never store empty passwords.
* **Invalid stored hash**: ``verify_password`` returns ``False`` (no exception) so login
  paths can stay uniform.
* **Rehashing**: Argon2 parameters can change over time; ``password_needs_rehash`` supports
  transparent upgrades on next successful login (application concern).
"""

import pytest
from app.core.security.passwords import hash_password, password_needs_rehash, verify_password


def test_password_hash_is_not_plaintext():
    """Checklist (1): digest must differ from the secret string."""
    raw = "a_strong_passphrase_here_123"
    h = hash_password(raw)
    assert h != raw
    assert not h.startswith(raw)


def test_verify_password_accepts_correct_and_rejects_wrong_secret():
    """Checklist (2): verification succeeds only for the original password."""
    raw = "correct_horse_battery_staple_99"
    h = hash_password(raw)
    assert verify_password(raw, h) is True
    assert verify_password("wrong_guess", h) is False


def test_hash_rejects_empty_password():
    with pytest.raises(ValueError, match="empty"):
        hash_password("")


def test_verify_handles_invalid_hash_gracefully():
    assert verify_password("x", "not-a-valid-argon-hash") is False


def test_password_needs_rehash_false_for_fresh_hash():
    h = hash_password("valid_password_12345")
    assert password_needs_rehash(h) is False
