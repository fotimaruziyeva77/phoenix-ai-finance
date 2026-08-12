"""
Centralized **public widget origin / hostname allowlist** policy (bootstrap + chat).

Normalization strategy
----------------------
1. **Request hostname** comes from the browser ``Origin`` header (preferred) or ``Referer``,
   parsed with :func:`app.lib.widget_allowed_domains.normalize_widget_hostname` (trim,
   lowercase, strip only a **trailing** dot, URL → host, drop default ports in the host part).

2. **Stored allowlist entries** are normalized when saved via
   :func:`app.lib.widget_allowed_domains.normalize_allowed_domains`:

   * **Exact host** — ``www.example.com``.
   * **Wildcard** — ``*.example.com`` matches one or more labels under ``example.com``
     (e.g. ``app.example.com``) but **not** the apex ``example.com``. The suffix must contain
     at least one dot (rejects ``*.com``) without relying on a public-suffix list.
   * **Apex + subdomains** — ``.example.com`` matches ``example.com`` and every
     ``*.example.com`` subtree. Leading dot is preserved in storage (see storage normalizer).

3. **Empty allowlist** — Default **open** in non-strict deployments (local/docker): any caller,
   including missing ``Origin``/``Referer``. In **strict** deployments (staging/production), empty
   allowlist **denies** embeds unless ops sets ``APP_PUBLIC_WIDGET_ALLOW_EMPTY_ORIGIN_ALLOWLIST=true``
   (logged as unsafe). Override locally with ``APP_PUBLIC_WIDGET_FORCE_DENY_EMPTY_ORIGIN_ALLOWLIST``.

4. **Non-empty allowlist + unknown host** — If neither header yields a host, **deny**.

5. **Loopback** — When :attr:`WidgetOriginPolicyOptions.loopback_aliases_equivalent` is true
   (default), ``localhost``, ``127.0.0.1``, ``::1``, and ``[::1]`` are interchangeable if
   **any** loopback host appears in the list (so dev can list only ``localhost`` while Vite uses
   ``127.0.0.1``).

6. **Opaque Origin** — Literal ``Origin: null`` is ignored; ``Referer`` is still used when present.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.lib.widget_allowed_domains import normalize_widget_hostname

_LOOPBACK_CANONICAL: frozenset[str] = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
        "[::1]",
    }
)


@dataclass(frozen=True, slots=True)
class WidgetOriginPolicyOptions:
    """Runtime toggles for origin checks (from :class:`app.core.config.Settings`)."""

    loopback_aliases_equivalent: bool = True
    deny_empty_allowlist: bool = False


def _coerce_allowed_strings(entries: Iterable[object]) -> list[str]:
    """Trim whitespace only; preserve leading ``.`` / ``*.`` semantics."""
    out: list[str] = []
    for e in entries:
        if isinstance(e, str):
            s = e.strip()
            if s:
                out.append(s.lower())
    return out


def _normalize_request_host(hostname: str | None) -> str | None:
    if not hostname:
        return None
    h = normalize_widget_hostname(hostname)
    return h if h else None


def _pattern_allows_request(entry_norm: str, request_norm: str) -> bool:
    if entry_norm.startswith("*."):
        suffix = entry_norm[2:]
        if not suffix:
            return False
        if request_norm == suffix:
            return False
        return request_norm.endswith("." + suffix)
    if entry_norm.startswith(".") and len(entry_norm) > 1:
        base = entry_norm[1:]
        if not base:
            return False
        return request_norm == base or request_norm.endswith("." + base)
    return request_norm == entry_norm


def _loopback_equivalent_match(request_norm: str, entry_norm: str, *, equivalent: bool) -> bool:
    if not equivalent:
        return False
    return entry_norm in _LOOPBACK_CANONICAL and request_norm in _LOOPBACK_CANONICAL


def widget_request_origin_allowed(
    request_hostname: str | None,
    allowed_entries: list[object],
    *,
    options: WidgetOriginPolicyOptions | None = None,
) -> bool:
    """
    Return True if the caller hostname is allowed for this widget configuration.

    ``allowed_entries`` is typically ``widget_config.allowed_domains_json`` (may be empty).
    """
    opts = options or WidgetOriginPolicyOptions()
    allowed = _coerce_allowed_strings(allowed_entries)
    if not allowed:
        return not opts.deny_empty_allowlist

    req = _normalize_request_host(request_hostname)
    if not req:
        return False

    for entry in allowed:
        if _pattern_allows_request(entry, req):
            return True
        if _loopback_equivalent_match(req, entry, equivalent=opts.loopback_aliases_equivalent):
            return True

    return False
