"""
Resend.com API client wrapper.

Thin async wrapper around the synchronous ``resend`` SDK — runs the blocking
send in a thread pool so it never blocks the event loop.

Fail-open: email errors are logged but never raise to callers.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.core.config import Settings

_LOG = get_logger(__name__)


class ResendEmailClient:
    """
    Send transactional emails via Resend.com.

    Usage::

        client = ResendEmailClient(settings)
        ok = await client.send(
            to="user@example.com",
            subject="Hello",
            html="<p>Hello!</p>",
        )
    """

    def __init__(self, settings: Settings) -> None:
        self._api_key = (settings.resend_api_key or "").strip()
        self._from_address = (settings.email_from_address or "").strip()
        self._from_name = (settings.email_from_name or "BotForge AI").strip()
        self._enabled = bool(self._api_key)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def from_field(self) -> str:
        return f"{self._from_name} <{self._from_address}>"

    async def send(
        self,
        *,
        to: str,
        subject: str,
        html: str,
    ) -> bool:
        """
        Send an email. Returns True on success, False on any error.
        Never raises — always fail-open.
        """
        if not self._enabled:
            _LOG.warning(
                "email_send_skipped",
                reason="resend_api_key_not_configured",
                to_domain=to.split("@")[-1] if "@" in to else "?",
            )
            return False

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._send_sync(to=to, subject=subject, html=html),
            )
            _LOG.info(
                "email_sent",
                to_domain=to.split("@")[-1] if "@" in to else "?",
                subject=subject[:60],
                resend_id=result,
            )
            return True
        except Exception as exc:
            _LOG.warning(
                "email_send_failed",
                error_type=type(exc).__name__,
                message=str(exc)[:200],
                to_domain=to.split("@")[-1] if "@" in to else "?",
            )
            return False

    def _send_sync(self, *, to: str, subject: str, html: str) -> str:
        """Blocking Resend SDK call — run in executor."""
        import resend  # lazy import so app starts without resend installed

        resend.api_key = self._api_key
        response = resend.Emails.send(
            {
                "from": self.from_field,
                "to": [to],
                "subject": subject,
                "html": html,
            }
        )
        return str(response.get("id", ""))
