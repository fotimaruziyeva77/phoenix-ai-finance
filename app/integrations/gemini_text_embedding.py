"""Google Generative Language ``embedContent`` (Gemini API) — text embeddings only."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from app.core.logging import get_logger

_LOG = get_logger(__name__)

# Prefer :class:`~app.core.config.Settings` (``EMBEDDING_MODEL`` / semantic-cache field); this
# fallback matches when ``model=`` is omitted or empty.
_DEFAULT_EMBEDDING_RESOURCE = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004").strip() or "models/text-embedding-004"


class GeminiEmbeddingError(RuntimeError):
    """Raised when ``fail_open=False`` and the embedding API returns an error or unusable payload."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        model_slug: str = "",
        response_body_snippet: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.model_slug = model_slug
        self.response_body_snippet = response_body_snippet


def _slug_from_embedding_resource(resource: str) -> str:
    s = (resource or "").strip()
    while s.lower().startswith("models/"):
        s = s[7:].strip()
    return s


def _embedding_slug_and_resource(model: str | None) -> tuple[str, str]:
    """
    Return ``(slug, resource)`` for URL ``.../v1/models/{slug}:embedContent`` and JSON ``"model": resource``.

    ``resource`` is always ``models/<slug>``. Unprefixed env values are accepted; ``EMBEDDING_MODEL``
    default is ``models/text-embedding-004`` (via :func:`os.getenv`).
    """
    raw = (model or "").strip() or _DEFAULT_EMBEDDING_RESOURCE
    slug = _slug_from_embedding_resource(raw)
    if not slug:
        slug = _slug_from_embedding_resource(_DEFAULT_EMBEDDING_RESOURCE)
    if not slug:
        slug = _slug_from_embedding_resource(os.getenv("EMBEDDING_MODEL", "models/text-embedding-004"))
    if not slug:
        tail = _DEFAULT_EMBEDDING_RESOURCE.rstrip("/").rsplit("/", 1)[-1]
        slug = tail.strip() or "text-embedding-004"
    resource = f"models/{slug}"
    return slug, resource


def _embedding_v1_root_from_chat_base(chat_base_url: str) -> str:
    """
    ``embedContent`` uses the **v1** API root, not v1beta (``generateContent`` may stay on v1beta).

    * ``.../v1beta`` → ``.../v1``
    * ``.../v1`` → unchanged
    """
    b = (chat_base_url or "").strip().rstrip("/")
    if not b:
        return "https://generativelanguage.googleapis.com/v1"
    bl = b.lower()
    if bl.endswith("/v1beta"):
        return b[: -len("v1beta")] + "v1"
    if bl.endswith("/v1"):
        return b
    return f"{b}/v1"


def _snippet_from_response(response: httpx.Response, limit: int = 800) -> str:
    try:
        t = (response.text or "").strip()
    except Exception:
        return ""
    return t[:limit]


def _fail_embedding(
    message: str,
    *,
    fail_open: bool,
    status_code: int | None,
    model_slug: str,
    response_body_snippet: str | None,
    log_event: str,
    extra: dict[str, Any],
) -> list[float] | None:
    _LOG.warning(
        log_event,
        model_slug=model_slug,
        http_status=status_code,
        fail_open=fail_open,
        **extra,
    )
    if fail_open:
        return None
    raise GeminiEmbeddingError(
        message,
        status_code=status_code,
        model_slug=model_slug,
        response_body_snippet=response_body_snippet,
    )


async def gemini_embed_text(
    *,
    api_key: str,
    base_url: str,
    model: str,
    text: str,
    client: httpx.AsyncClient,
    fail_open: bool = True,
) -> list[float] | None:
    """
    Return embedding ``values`` list.

    When ``fail_open`` is True (default), transport / HTTP / parse problems return ``None``.
    When ``fail_open`` is False, those failures raise :class:`GeminiEmbeddingError`.
    """
    key = (api_key or "").strip()
    if not key:
        return None

    slug, model_resource = _embedding_slug_and_resource(model)
    root = _embedding_v1_root_from_chat_base(base_url)
    url = f"{root}/models/{slug}:embedContent"
    payload: dict[str, Any] = {
        "model": model_resource,
        "content": {"parts": [{"text": (text or "")[:8000]}]},
    }

    try:
        r = await client.post(
            url,
            json=payload,
            headers={"x-goog-api-key": key},
        )
    except httpx.TimeoutException as exc:
        return _fail_embedding(
            f"Gemini embedding timeout: {exc}",
            fail_open=fail_open,
            status_code=None,
            model_slug=slug,
            response_body_snippet=None,
            log_event="gemini_embed_transport_error",
            extra={"exc_type": type(exc).__name__, "error_detail": str(exc)[:400]},
        )
    except httpx.HTTPError as exc:
        return _fail_embedding(
            f"Gemini embedding transport error: {exc}",
            fail_open=fail_open,
            status_code=getattr(getattr(exc, "response", None), "status_code", None),
            model_slug=slug,
            response_body_snippet=None,
            log_event="gemini_embed_transport_error",
            extra={"exc_type": type(exc).__name__, "error_detail": str(exc)[:400]},
        )

    if r.status_code >= 400:
        snippet = _snippet_from_response(r)
        return _fail_embedding(
            f"Gemini embedding HTTP {r.status_code}",
            fail_open=fail_open,
            status_code=r.status_code,
            model_slug=slug,
            response_body_snippet=snippet[:800],
            log_event="gemini_embed_http_error",
            extra={
                "request_path": f"/v1/models/{slug}:embedContent",
                "embedding_api_root": root,
                "response_body_snippet": snippet[:800],
            },
        )

    try:
        body = r.json()
    except (json.JSONDecodeError, ValueError) as exc:
        return _fail_embedding(
            f"Gemini embedding invalid JSON: {exc}",
            fail_open=fail_open,
            status_code=r.status_code,
            model_slug=slug,
            response_body_snippet=_snippet_from_response(r),
            log_event="gemini_embed_parse_error",
            extra={"exc_type": type(exc).__name__},
        )

    if not isinstance(body, dict):
        return _fail_embedding(
            "Gemini embedding response root is not a JSON object.",
            fail_open=fail_open,
            status_code=r.status_code,
            model_slug=slug,
            response_body_snippet=_snippet_from_response(r),
            log_event="gemini_embed_parse_error",
            extra={"reason": "non_object_json"},
        )

    emb = body.get("embedding")
    if not isinstance(emb, dict):
        return _fail_embedding(
            "Gemini embedding payload missing embedding object.",
            fail_open=fail_open,
            status_code=r.status_code,
            model_slug=slug,
            response_body_snippet=_snippet_from_response(r),
            log_event="gemini_embed_parse_error",
            extra={"reason": "missing_embedding"},
        )

    values = emb.get("values")
    if not isinstance(values, list) or not values:
        return _fail_embedding(
            "Gemini embedding payload missing values array.",
            fail_open=fail_open,
            status_code=r.status_code,
            model_slug=slug,
            response_body_snippet=_snippet_from_response(r),
            log_event="gemini_embed_parse_error",
            extra={"reason": "empty_values"},
        )

    out: list[float] = []
    for v in values:
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            return _fail_embedding(
                "Gemini embedding values are not numeric.",
                fail_open=fail_open,
                status_code=r.status_code,
                model_slug=slug,
                response_body_snippet=_snippet_from_response(r),
                log_event="gemini_embed_parse_error",
                extra={"reason": "non_numeric_component"},
            )

    _LOG.debug(
        "gemini_embed_ok",
        model_slug=slug,
        dimensions=len(out),
        text_chars=min(len(text or ""), 8000),
    )
    return out


__all__ = ["GeminiEmbeddingError", "gemini_embed_text"]
