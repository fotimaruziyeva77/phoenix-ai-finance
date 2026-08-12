"""Normalize and validate hostname lists for widget embed allowlists."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from app.lib.widget_origin_policy import WidgetOriginPolicyOptions

# Match dashboard/API expectations; large enough for multi-domain sites.
MAX_ALLOWED_DOMAINS = 64
# RFC 1035 / common browser limits; full host string (no port).
MAX_DOMAIN_HOST_LEN = 253


def normalize_widget_hostname(value: str) -> str:
    """Normalize a single hostname or URL host part (used for request Origin/Referer)."""
    return _parse_one_host(value)


def normalize_allowlist_entry_for_storage(raw: str) -> str:
    """
    Normalize one allowlist entry for JSON storage.

    Preserves ``*.`` and leading ``.`` wildcard semantics (apex+subdomains). Full URLs are still
    accepted for plain host entries.
    """
    s = raw.strip()
    if not s:
        return ""
    sl = s.lower()
    if sl.startswith("*."):
        suffix_src = sl[2:].strip()
        if "://" in suffix_src or "/" in suffix_src:
            raise ValueError("wildcard allowlist entry cannot be a URL; use *.example.com")
        inner = _parse_one_host(suffix_src)
        if not inner:
            raise ValueError("invalid wildcard allowlist entry")
        if "." not in inner:
            raise ValueError("wildcard entries must look like *.example.com, not *.com")
        if ".." in inner or inner.startswith("."):
            raise ValueError("invalid wildcard allowlist entry")
        return "*." + inner
    if sl.startswith(".") and len(sl) > 1 and "://" not in sl:
        rest = sl[1:].strip()
        inner = _parse_one_host(rest)
        if not inner:
            raise ValueError("invalid leading-dot allowlist entry")
        if "." not in inner:
            raise ValueError("leading-dot entries must look like .example.com")
        if ".." in inner or inner.startswith("."):
            raise ValueError("invalid leading-dot allowlist entry")
        return "." + inner
    return _parse_one_host(raw)


def normalize_allowed_domains(
    hosts: Iterable[str],
    *,
    allow_wildcard_patterns: bool = True,
) -> list[str]:
    """
    Normalize hostnames for storage and comparison.

    * strips ASCII whitespace
    * lowercases
    * strips a single trailing dot (FQDN form) on plain hosts
    * optional ``*.example.com`` (subdomains only) and ``.example.com`` (apex + subdomains)
    * if a plain value looks like a URL, extracts the host (scheme + netloc)
    * drops duplicates while preserving first-seen order
    * enforces non-empty labels and length caps

    Raises:
        ValueError: invalid or empty entry, too many hosts, host too long, or wildcard patterns
        when ``allow_wildcard_patterns`` is false.
    """
    seen: set[str] = set()
    out: list[str] = []

    for raw in hosts:
        host = normalize_allowlist_entry_for_storage(raw)
        if not host:
            raise ValueError("domain entries must be non-empty")
        if not allow_wildcard_patterns and (
            host.startswith("*.") or (host.startswith(".") and len(host) > 1)
        ):
            raise ValueError(
                "wildcard allowlist patterns (*.example.com or .example.com) are disabled; "
                "list explicit hostnames or set APP_PUBLIC_WIDGET_ALLOW_ALLOWLIST_WILDCARD_PATTERNS=true"
            )
        if len(host) > MAX_DOMAIN_HOST_LEN:
            raise ValueError(f"domain exceeds {MAX_DOMAIN_HOST_LEN} characters")
        if host not in seen:
            seen.add(host)
            out.append(host)

    if len(out) > MAX_ALLOWED_DOMAINS:
        raise ValueError(f"at most {MAX_ALLOWED_DOMAINS} allowed domains")

    return out


def _parse_one_host(raw: str) -> str:
    s = raw.strip()
    if not s:
        return ""

    lower = s.lower()
    if "://" in lower or lower.startswith("//"):
        url = lower if "://" in lower else f"https:{lower}"
        parsed = urlparse(url)
        host = (parsed.hostname or "").strip().lower()
        if not host and parsed.netloc:
            chunk = parsed.netloc.split("@")[-1].strip().lower()
            if chunk.startswith("[") and "]" in chunk:
                end = chunk.index("]")
                host = chunk[: end + 1].lower()
            elif ":" in chunk and not chunk.startswith("["):
                host = chunk.rsplit(":", 1)[0]
            else:
                host = chunk
    else:
        host = lower.split("/")[0].split("@")[-1]
        if host.startswith("[") and "]" in host:
            end = host.index("]")
            host = host[: end + 1].lower()
        elif ":" in host:
            host = host.rsplit(":", 1)[0]

    return host.strip().strip(".").lower()


def extract_hostname_from_origin_or_referer(
    origin: str | None,
    referer: str | None,
) -> str | None:
    """
    Best-effort host for browser embedding: ``Origin`` first, then ``Referer``.

    Browsers may send the literal ``"null"`` ``Origin`` for opaque/sandboxed contexts;
    that is treated as unknown (returns ``None``).
    """
    if origin and origin.strip().lower() != "null":
        h = _parse_one_host(origin)
        if h:
            return h
    if referer:
        h = _parse_one_host(referer)
        if h:
            return h
    return None


def request_hostname_matches_allowlist(
    request_hostname: str | None,
    allowed_hosts: list,
    *,
    options: WidgetOriginPolicyOptions | None = None,
) -> bool:
    """
    Delegate to :func:`app.lib.widget_origin_policy.widget_request_origin_allowed`.

    Kept as a thin wrapper for older call sites and tests importing this module.
    """
    from app.lib.widget_origin_policy import widget_request_origin_allowed

    return widget_request_origin_allowed(request_hostname, allowed_hosts, options=options)
