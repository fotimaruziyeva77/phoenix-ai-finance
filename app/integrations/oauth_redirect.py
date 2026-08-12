"""Build frontend redirect URLs for browser OAuth flows."""

from __future__ import annotations

from urllib.parse import urlencode


def append_oauth_query_params(base_url: str, params: dict[str, str]) -> str:
    filtered = {k: v for k, v in params.items() if v}
    if not filtered:
        return base_url
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}{urlencode(filtered)}"
