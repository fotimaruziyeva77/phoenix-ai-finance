"""Owner-scoped widget configuration (create, read, update)."""

from __future__ import annotations

import uuid

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.lib.public_widget_key import generate_public_widget_key
from app.lib.widget_allowed_domains import normalize_allowed_domains
from app.models.user import User
from app.models.widget_config import WidgetConfig
from app.repositories.bot_repository import BotRepository
from app.schemas.widget_config import WidgetConfigRead, WidgetConfigUpdate
from app.services.bot_exceptions import BotForbiddenError, BotNotFoundError
from app.services.widget_config_exceptions import (
    WidgetConfigNotFoundError,
    WidgetConfigPersistenceError,
    WidgetConfigValidationError,
)

_MAX_PUBLIC_KEY_FLUSH_ATTEMPTS = 4

_ADVISORY_LOCK_SQL = text(
    "SELECT pg_advisory_xact_lock(abs(hashtext(CAST(:bid AS text))))",
)


class WidgetConfigService:
    """Manage embed widget rows for bots the user owns."""

    def __init__(self, session: AsyncSession, bot_repo: BotRepository, settings: Settings) -> None:
        self._session = session
        self._bots = bot_repo
        self._settings = settings

    async def get_or_create_widget_config_for_bot(self, owner: User, bot_id: uuid.UUID) -> WidgetConfigRead:
        await self._ensure_bot_owned(owner, bot_id)
        existing = await self._get_primary_widget(owner_id=owner.id, bot_id=bot_id)
        if existing is not None:
            return WidgetConfigRead.model_validate(existing)

        await self._session.execute(_ADVISORY_LOCK_SQL, {"bid": str(bot_id)})
        existing = await self._get_primary_widget(owner_id=owner.id, bot_id=bot_id)
        if existing is not None:
            return WidgetConfigRead.model_validate(existing)

        wc: WidgetConfig | None = None
        for _ in range(_MAX_PUBLIC_KEY_FLUSH_ATTEMPTS):
            try:
                async with self._session.begin_nested():
                    row = WidgetConfig(
                        bot_id=bot_id,
                        owner_id=owner.id,
                        public_widget_key=generate_public_widget_key(),
                    )
                    self._session.add(row)
                    await self._session.flush()
                    await self._session.refresh(row)
                wc = row
                break
            except IntegrityError:
                dup = await self._get_primary_widget(owner_id=owner.id, bot_id=bot_id)
                if dup is not None:
                    wc = dup
                    break
        else:
            raise WidgetConfigPersistenceError("Could not allocate a unique widget public key")

        assert wc is not None
        try:
            await self._bots.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise WidgetConfigPersistenceError() from exc

        return WidgetConfigRead.model_validate(wc)

    async def get_widget_config_for_owner(self, owner: User, bot_id: uuid.UUID) -> WidgetConfigRead:
        await self._ensure_bot_owned(owner, bot_id)
        row = await self._get_primary_widget(owner_id=owner.id, bot_id=bot_id)
        if row is None:
            raise WidgetConfigNotFoundError()
        return WidgetConfigRead.model_validate(row)

    async def update_widget_config_for_bot(
        self,
        owner: User,
        bot_id: uuid.UUID,
        payload: WidgetConfigUpdate,
    ) -> WidgetConfigRead:
        await self._ensure_bot_owned(owner, bot_id)
        row = await self._get_primary_widget(owner_id=owner.id, bot_id=bot_id)
        if row is None:
            raise WidgetConfigNotFoundError()

        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return WidgetConfigRead.model_validate(row)

        if "allowed_domains_json" in updates:
            raw = updates["allowed_domains_json"]
            assert raw is not None
            try:
                row.allowed_domains_json = normalize_allowed_domains(
                    raw,
                    allow_wildcard_patterns=self._settings.public_widget_allow_allowlist_wildcard_patterns_effective,
                )
            except ValueError as exc:
                raise WidgetConfigValidationError(str(exc)) from exc

        if "is_enabled" in updates:
            row.is_enabled = bool(updates["is_enabled"])

        if "theme" in updates:
            t = updates["theme"]
            if t is not None:
                t = t.strip()
            row.theme = t if t else None

        if "welcome_text" in updates:
            w = updates["welcome_text"]
            if w is not None:
                w = w.strip()
            row.welcome_text = w if w else None

        if "pre_chat_form_json" in updates:
            pcf = updates["pre_chat_form_json"]
            if pcf is not None:
                row.pre_chat_form_json = [
                    f.model_dump() if hasattr(f, "model_dump") else f for f in pcf
                ]
            else:
                row.pre_chat_form_json = None

        if "custom_css" in updates:
            css = updates["custom_css"]
            if css is not None:
                css = css.strip()
            row.custom_css = css if css else None

        if "widget_settings_json" in updates:
            row.widget_settings_json = updates["widget_settings_json"]

        try:
            await self._session.flush()
            await self._session.refresh(row)
            await self._bots.commit()
            return WidgetConfigRead.model_validate(row)
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise WidgetConfigPersistenceError() from exc

    async def _ensure_bot_owned(self, owner: User, bot_id: uuid.UUID) -> None:
        bot = await self._bots.get_bot_by_id(owner_id=owner.id, bot_id=bot_id)
        if bot is not None:
            return
        if await self._bots.exists_by_id(bot_id=bot_id):
            raise BotForbiddenError()
        raise BotNotFoundError()

    async def _get_primary_widget(self, *, owner_id: uuid.UUID, bot_id: uuid.UUID) -> WidgetConfig | None:
        stmt = (
            select(WidgetConfig)
            .where(
                WidgetConfig.bot_id == bot_id,
                WidgetConfig.owner_id == owner_id,
            )
            .order_by(WidgetConfig.created_at.asc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
