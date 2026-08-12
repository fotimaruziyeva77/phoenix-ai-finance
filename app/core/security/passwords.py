"""Argon2id password hashing (no logging of secrets)."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(raw_password: str) -> str:
    """
    Hash a plaintext password for storage.

    Raises:
        TypeError: if ``raw_password`` is not a string.
        ValueError: if empty (do not hash empty passwords).
    """
    if not isinstance(raw_password, str):
        raise TypeError("raw_password must be a str")
    if not raw_password:
        raise ValueError("raw_password must not be empty")
    return _hasher.hash(raw_password)


def verify_password(raw_password: str, hashed_password: str) -> bool:
    """
    Verify ``raw_password`` against a stored Argon2 hash.

    Constant-time comparison is handled by the Argon2 implementation.

    Returns:
        True if the password matches, False otherwise (including malformed hashes).
    """
    if not isinstance(raw_password, str) or not isinstance(hashed_password, str):
        return False
    if not hashed_password:
        return False
    try:
        _hasher.verify(hashed_password, raw_password)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


def password_needs_rehash(hashed_password: str) -> bool:
    """Return True if the hash should be upgraded to current Argon2 parameters."""
    if not hashed_password:
        return False
    try:
        return _hasher.check_needs_rehash(hashed_password)
    except InvalidHashError:
        return True
