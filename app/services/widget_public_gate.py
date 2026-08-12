"""Shared public-widget access checks (bootstrap + chat)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.widget_allowed_domains import (
    extract_hostname_from_origin_or_referer,
    request_hostname_matches_allowlist,
)
from app.lib.widget_origin_policy import WidgetOriginPolicyOptions
from app.models.bot import Bot
from app.models.widget_config import WidgetConfig
from app.services.widget_bootstrap_exceptions import (
    WidgetBootstrapDisabledError,
    WidgetBootstrapOriginForbiddenError,
)


async def load_widget_and_bot_by_public_key(
    session: AsyncSession,
    public_widget_key: str,
) -> tuple[WidgetConfig, Bot] | None:
    """Return widget row and bot, or ``None`` if the key is unknown."""
    key = public_widget_key.strip()
    if not key:
        return None
    stmt = (
        select(WidgetConfig, Bot)
        .join(Bot, WidgetConfig.bot_id == Bot.id)
        .where(WidgetConfig.public_widget_key == key)
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        return None
    return row[0], row[1]


def enforce_public_widget_origin_and_enabled(
    wc: WidgetConfig,
    *,
    origin_header: str | None,
    referer_header: str | None,
    origin_policy: WidgetOriginPolicyOptions | None = None,
) -> None:
    if not wc.is_enabled:
        raise WidgetBootstrapDisabledError()
    request_host = extract_hostname_from_origin_or_referer(origin_header, referer_header)
    allowed = list(wc.allowed_domains_json or [])
    if not request_hostname_matches_allowlist(request_host, allowed, options=origin_policy):
        raise WidgetBootstrapOriginForbiddenError()
