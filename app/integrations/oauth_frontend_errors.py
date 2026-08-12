"""Build frontend OAuth redirect URLs with stable error query params."""

from __future__ import annotations

from app.integrations.oauth_redirect import append_oauth_query_params


def frontend_oauth_error_url(
    frontend_base: str,
    *,
    oauth_error_code: str,
    detail: str | None = None,
    expose_error_details: bool = False,
) -> str:
    payload: dict[str, str] = {"oauth_error": oauth_error_code}
    if detail and expose_error_details:
        payload["oauth_error_detail"] = detail[:500]
    return append_oauth_query_params(frontend_base, payload)
