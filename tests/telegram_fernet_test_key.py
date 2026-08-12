"""Shared Fernet key for Telegram-related integration tests (do not use in production)."""

from __future__ import annotations

from cryptography.fernet import Fernet

TELEGRAM_FERNET_INTEGRATION_KEY = Fernet.generate_key().decode()
