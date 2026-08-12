"""
Structured auth audit events (stdout / log aggregation).

Never log passwords, tokens, refresh tokens, OAuth codes, or exchange codes.
"""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.core.logging import get_logger

_LOG = get_logger("auth_audit")


def _safe_user_id(user_id: uuid.UUID | str | None) -> str | None:
    if user_id is None:
        return None
    return str(user_id)


def log_auth_event(
    event: str,
    *,
    outcome: str,
    client_ip: str | None = None,
    reason_code: str | None = None,
    user_id: uuid.UUID | str | None = None,
    role: str | None = None,
    email_domain: str | None = None,
    provider: str | None = None,
    tenant_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    ``event`` examples: auth.register, auth.login, auth.refresh, auth.logout,
    auth.oauth_callback, auth.oauth_exchange.

    ``outcome``: success | failure

    Reserved optional dimensions for later features:
    ``role`` (e.g. superadmin), ``tenant_id``, subscriptions can add plan_key here later.
    """
    payload: dict[str, Any] = {
        "audit": True,
        "audit_event": event,
        "outcome": outcome,
    }
    if client_ip is not None:
        payload["client_ip"] = client_ip
    if reason_code is not None:
        payload["reason_code"] = reason_code
    uid = _safe_user_id(user_id)
    if uid is not None:
        payload["user_id"] = uid
    if role is not None:
        payload["role"] = role
    if email_domain is not None:
        payload["email_domain"] = email_domain
    if provider is not None:
        payload["oauth_provider"] = provider
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
    if extra:
        for k, v in extra.items():
            if k not in payload:
                payload[k] = v

    _LOG.info("auth_audit", **payload)


def audit_oauth_callback_redirect(*, provider: str, client_ip: str | None, redirect_url: str) -> None:
    """Infer success (exchange code issued) vs failure (oauth_error) from the frontend redirect URL."""

    q = parse_qs(urlparse(redirect_url).query)
    err = (q.get("oauth_error") or [None])[0]
    if err:
        log_auth_event(
            "auth.oauth_callback",
            outcome="failure",
            client_ip=client_ip,
            provider=provider,
            reason_code=str(err),
        )
        return
    if q.get("oauth_exchange_code"):
        log_auth_event(
            "auth.oauth_callback",
            outcome="success",
            client_ip=client_ip,
            provider=provider,
        )
        return
    log_auth_event(
        "auth.oauth_callback",
        outcome="failure",
        client_ip=client_ip,
        provider=provider,
        reason_code="oauth_redirect_missing_params",
    )
