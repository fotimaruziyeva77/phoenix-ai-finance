"""Cryptographic public widget identifiers (embed token)."""

from __future__ import annotations

import secrets

# 256 bits — collision probability is negligible; not sequential.
_KEY_ENTROPY_BYTES = 32


def generate_public_widget_key() -> str:
    """Return a URL-safe opaque key suitable for ``WidgetConfig.public_widget_key``."""
    return secrets.token_urlsafe(_KEY_ENTROPY_BYTES)
