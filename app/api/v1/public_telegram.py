"""Unauthenticated Telegram Bot API webhook ingress (validated via secret header)."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import DbSession, TelegramConfigServiceDep, TelegramWebhookInboundServiceDep, rate_limit_telegram_webhook
from app.core.logging import get_logger
from app.repositories.webhook_log_repository import WebhookLogRepository

router = APIRouter(tags=["public-telegram"])
_LOG = get_logger(__name__)

_TELEGRAM_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
_MAX_UPDATE_BYTES = 512_000


def _peek_telegram_update(body: bytes) -> dict[str, Any]:
    """Lightweight parse for logs only (no message body content)."""
    out: dict[str, Any] = {"update_id": None, "update_keys": None}
    try:
        o = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return out
    if not isinstance(o, dict):
        return out
    uid = o.get("update_id")
    out["update_id"] = uid if isinstance(uid, int) else None
    out["update_keys"] = sorted(k for k in o.keys() if isinstance(k, str))[:24]
    return out


@router.post(
    "/public/telegram/{bot_id}/webhook",
    status_code=status.HTTP_200_OK,
    summary="Telegram Bot API webhook (public)",
    description=(
        "Receives Telegram ``Update`` JSON. The route is not authenticated with JWT; "
        "requests must present a valid ``X-Telegram-Bot-Api-Secret-Token`` matching the "
        "value registered with Telegram at connect time."
    ),
    response_class=Response,
    dependencies=[Depends(rate_limit_telegram_webhook)],
)
async def telegram_bot_webhook(
    bot_id: UUID,
    request: Request,
    telegram_service: TelegramConfigServiceDep,
    inbound: TelegramWebhookInboundServiceDep,
    session: DbSession,
) -> Response:
    from datetime import UTC, datetime as _dt

    body = await request.body()
    if len(body) > _MAX_UPDATE_BYTES:
        return Response(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    peek = _peek_telegram_update(body)
    update_keys = peek.get("update_keys") or []
    event_type = update_keys[0] if update_keys else "telegram_update"

    _LOG.info(
        "telegram_webhook_ingress",
        bot_id=str(bot_id),
        body_bytes=len(body),
        update_id=peek.get("update_id"),
        update_keys=update_keys,
        has_secret_header=bool(request.headers.get(_TELEGRAM_SECRET_HEADER)),
        path=str(request.url.path),
    )

    secret = request.headers.get(_TELEGRAM_SECRET_HEADER)
    ok = await telegram_service.verify_telegram_webhook_request(
        bot_id,
        secret_header_value=secret,
    )
    if not ok:
        _LOG.warning(
            "telegram_webhook_verify_failed",
            bot_id=str(bot_id),
            body_bytes=len(body),
            update_id=peek.get("update_id"),
            hint="Wrong/missing X-Telegram-Bot-Api-Secret-Token, or bot Telegram row not active/connected",
        )
        # Log failed verification
        try:
            wh_repo = WebhookLogRepository(session)
            await wh_repo.create(
                source="telegram", event_type=event_type, status="failed",
                error_message="webhook_verify_failed",
                payload_preview={"update_id": peek.get("update_id"), "update_keys": update_keys},
                bot_id=bot_id, processed_at=_dt.now(UTC),
            )
            await wh_repo.commit()
        except Exception:  # noqa: BLE001
            pass
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    log_status = "processed"
    error_msg: str | None = None
    try:
        await inbound.handle_raw_update(bot_id=bot_id, raw_body=body)
    except Exception as exc:  # noqa: BLE001
        log_status = "failed"
        error_msg = str(exc)[:500]
        raise
    finally:
        try:
            wh_repo = WebhookLogRepository(session)
            await wh_repo.create(
                source="telegram", event_type=event_type, status=log_status,
                error_message=error_msg,
                payload_preview={"update_id": peek.get("update_id"), "update_keys": update_keys},
                bot_id=bot_id, processed_at=_dt.now(UTC),
            )
            await wh_repo.commit()
        except Exception:  # noqa: BLE001
            pass

    _LOG.info(
        "telegram_webhook_handled",
        bot_id=str(bot_id),
        update_id=peek.get("update_id"),
    )
    return Response(status_code=status.HTTP_200_OK)
