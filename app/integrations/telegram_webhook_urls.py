"""
Build canonical Telegram webhook URLs for BotForge (path + absolute URL).

The path uses the BotForge ``bot_id`` (UUID v4) so it is not sequentially guessable.
Authentication for inbound requests is enforced via Telegram ``secret_token`` (stored encrypted)
and the ``X-Telegram-Bot-Api-Secret-Token`` header — not via obscurity of the URL alone.
"""

from __future__ import annotations

import uuid


def telegram_webhook_path_for_bot(bot_id: uuid.UUID) -> str:
    """Relative path under the API mount (includes ``/api/v1`` prefix)."""
    return f"/api/v1/public/telegram/{bot_id}/webhook"


def build_telegram_webhook_url(public_api_base_url: str, bot_id: uuid.UUID) -> str:
    """Full HTTPS URL passed to Telegram ``setWebhook``."""
    base = (public_api_base_url or "").strip().rstrip("/")
    return f"{base}{telegram_webhook_path_for_bot(bot_id)}"


def normalize_public_api_base_url(raw: str | None) -> str | None:
    s = (raw or "").strip().rstrip("/")
    return s if s else None


def public_base_url_allowed_for_telegram_webhook(*, base_url: str, environment: str) -> bool:
    """
    Telegram requires HTTPS for production webhooks.

    Non-production environments may use ``http://localhost`` / ``127.0.0.1`` for local tunnels.
    """
    b = base_url.strip().lower()
    if b.startswith("https://"):
        return True
    env = (environment or "").strip().lower()
    if env in ("production", "prod"):
        return False
    return b.startswith("http://localhost") or b.startswith("http://127.0.0.1")
