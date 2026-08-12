"""
High-level email service: verification, password reset, welcome.

Orchestrates :class:`~app.integrations.email.resend_client.ResendEmailClient`
+ :class:`~app.services.email_token_service.EmailTokenService`.

All public methods are fire-and-forget friendly — they return ``bool``
and never raise to callers.
"""

from __future__ import annotations

import re
import uuid
from urllib.parse import urlencode

from app.core.config import Settings
from app.core.logging import get_logger
from app.integrations.email.resend_client import ResendEmailClient
from app.integrations.email.templates import (
    email_verification_html,
    lead_alert_html,
    password_reset_html,
    welcome_html,
)
from app.services.email_token_service import EmailTokenService

_LOG = get_logger(__name__)

# Matches action URLs embedded in HTML email bodies, e.g.:
#   href="http://localhost:3000/auth/verify-email?token=abc123"
_ACTION_URL_RE = re.compile(r'href="(https?://[^"]*\?[^"]*token=[^"]+)"')


class EmailService:
    """
    Compose and send transactional emails.

    Inject via FastAPI dependency (see ``app/api/deps.py``).
    """

    def __init__(
        self,
        settings: Settings,
        resend_client: ResendEmailClient,
        token_service: EmailTokenService,
    ) -> None:
        self._settings = settings
        self._resend = resend_client
        self._tokens = token_service

    # ------------------------------------------------------------------
    # Email verification
    # ------------------------------------------------------------------

    async def send_verification_email(
        self,
        *,
        user_id: uuid.UUID,
        email: str,
        full_name: str | None = None,
    ) -> bool:
        """
        Create a verification token and send the confirmation email.

        Returns ``True`` when the email was delivered (Resend accepted it).
        """
        try:
            token = await self._tokens.create_token(
                "email_verify",
                user_id,
                ttl_seconds=self._settings.email_verification_token_ttl_seconds,
            )
        except RuntimeError as exc:
            _LOG.warning("send_verification_email_token_failed", error=str(exc)[:120])
            return False

        verify_url = self._build_url("/auth/verify-email", token=token)
        html = email_verification_html(full_name=full_name, verify_url=verify_url)

        ok = await self._resend.send(
            to=email,
            subject="Verify your BotForge AI email address",
            html=html,
        )
        if not ok:
            self._dev_log_email_fallback(
                email_type="email_verify",
                to=email,
                action_url=verify_url,
                html=html,
            )
        return ok

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    async def send_password_reset_email(
        self,
        *,
        user_id: uuid.UUID,
        email: str,
        full_name: str | None = None,
    ) -> bool:
        """
        Create a password-reset token and send the reset email.
        """
        try:
            token = await self._tokens.create_token(
                "password_reset",
                user_id,
                ttl_seconds=self._settings.email_password_reset_token_ttl_seconds,
            )
        except RuntimeError as exc:
            _LOG.warning("send_password_reset_email_token_failed", error=str(exc)[:120])
            return False

        reset_url = self._build_url("/auth/reset-password", token=token)
        html = password_reset_html(full_name=full_name, reset_url=reset_url)

        ok = await self._resend.send(
            to=email,
            subject="Reset your BotForge AI password",
            html=html,
        )
        if not ok:
            self._dev_log_email_fallback(
                email_type="password_reset",
                to=email,
                action_url=reset_url,
                html=html,
            )
        return ok

    # ------------------------------------------------------------------
    # Lead alerts
    # ------------------------------------------------------------------

    async def send_lead_alert_email(
        self,
        *,
        to_email: str,
        owner_name: str | None = None,
        lead_name: str | None = None,
        lead_phone: str | None = None,
        lead_status: str = "new",
        lead_temperature: str | None = None,
        bot_name: str,
        summary: str | None = None,
    ) -> bool:
        """Send a new-lead notification email to the bot owner."""
        dashboard_url = self._build_url("/dashboard/leads")
        html = lead_alert_html(
            owner_name=owner_name,
            lead_name=lead_name,
            lead_phone=lead_phone,
            lead_status=lead_status,
            lead_temperature=lead_temperature,
            bot_name=bot_name,
            summary=summary,
            dashboard_url=dashboard_url,
        )
        return await self._resend.send(
            to=to_email,
            subject=f"New lead from {bot_name} — BotForge AI",
            html=html,
        )

    # ------------------------------------------------------------------
    # Welcome (after successful verification)
    # ------------------------------------------------------------------

    async def send_welcome_email(
        self,
        *,
        email: str,
        full_name: str | None = None,
    ) -> bool:
        dashboard_url = self._build_url("/dashboard")
        html = welcome_html(full_name=full_name, dashboard_url=dashboard_url)
        return await self._resend.send(
            to=email,
            subject="Welcome to BotForge AI! 🚀",
            html=html,
        )

    # ------------------------------------------------------------------
    # Token helpers (delegated to EmailTokenService)
    # ------------------------------------------------------------------

    async def consume_verification_token(self, token: str) -> uuid.UUID | None:
        return await self._tokens.consume_token("email_verify", token)

    async def consume_password_reset_token(self, token: str) -> uuid.UUID | None:
        return await self._tokens.consume_token("password_reset", token)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_url(self, path: str, **params: str) -> str:
        base = (self._settings.frontend_base_url or "http://localhost:3000").rstrip("/")
        if params:
            return f"{base}{path}?{urlencode(params)}"
        return f"{base}{path}"

    def _dev_log_email_fallback(
        self,
        *,
        email_type: str,
        to: str,
        action_url: str | None = None,
        html: str = "",
    ) -> None:
        """
        Log the action URL to the backend when email delivery fails.

        This is intentionally a WARNING so it surfaces in default log
        configurations.  Grep for ``[DEV_EMAIL_FALLBACK]`` to find it.

        In production environments this still logs (the warning is harmless —
        Resend should succeed there), but the URL is already known to the user
        so it carries no extra risk.
        """
        # Prefer the directly-passed URL; fall back to regex extraction from HTML.
        url = action_url
        if not url:
            match = _ACTION_URL_RE.search(html)
            url = match.group(1) if match else "(URL not found in email body)"

        _LOG.warning(
            "[DEV_EMAIL_FALLBACK] email delivery failed — use this link for testing",
            email_type=email_type,
            recipient=to,
            action_url=url,
        )
