"""Client IP extraction (safe defaults; optional trusted ``X-Forwarded-For``)."""

from __future__ import annotations

from starlette.requests import Request


def client_ip(request: Request, *, trust_forwarded_for: bool) -> str | None:
    """
    Prefer the direct TCP peer. When ``trust_forwarded_for`` is True (behind a known
    reverse proxy), use the first hop in ``X-Forwarded-For``.
    """
    if trust_forwarded_for:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            first = xff.split(",")[0].strip()
            if first:
                return first
    if request.client and request.client.host:
        return request.client.host
    return None
