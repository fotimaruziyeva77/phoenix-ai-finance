"""Bot persistence with explicit owner-scoped access patterns."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot import Bot


@dataclass(slots=True)
class BotListFilters:
    """Search/filter foundation for owner-scoped bot lists."""

    statuses: tuple[str, ...] | None = None
    niche_ids: tuple[str, ...] | None = None
    goal_types: tuple[str, ...] | None = None
    search: str | None = None
    include_archived: bool = False


class BotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_bot(
        self,
        *,
        owner_id: uuid.UUID,
        name: str,
        niche_id: str,
        goal_type: str,
        status: str = "draft",
        primary_channel: str | None = None,
        welcome_message: str | None = None,
        tone: str | None = None,
        language: str | None = None,
        short_description: str | None = None,
        provider_name: str = "gemini",
        model_name: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> Bot:
        bot = Bot(
            owner_id=owner_id,
            name=name,
            niche_id=niche_id,
            goal_type=goal_type,
            status=status,
            primary_channel=primary_channel,
            welcome_message=welcome_message,
            tone=tone,
            language=language,
            short_description=short_description,
            provider_name=provider_name,
            model_name=model_name,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        self._session.add(bot)
        await self._session.flush()
        await self._session.refresh(bot)
        return bot

    async def get_bot_by_id(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> Bot | None:
        stmt = select(Bot).where(Bot.id == bot_id, Bot.owner_id == owner_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> bool:
        stmt = select(Bot.id).where(Bot.id == bot_id, Bot.owner_id == owner_id).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def exists_by_id(self, *, bot_id: uuid.UUID) -> bool:
        stmt = select(Bot.id).where(Bot.id == bot_id).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_bot_by_id_unscoped(self, *, bot_id: uuid.UUID) -> Bot | None:
        """Load bot by primary key (internal/public widget flows; not owner-scoped)."""
        stmt = select(Bot).where(Bot.id == bot_id).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_bots_by_owner(
        self,
        *,
        owner_id: uuid.UUID,
        filters: BotListFilters | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Bot]:
        stmt = self._build_owner_list_stmt(
            owner_id=owner_id,
            filters=filters,
        ).order_by(Bot.updated_at.desc()).offset(max(offset, 0)).limit(max(limit, 1))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_bots_by_owner(
        self,
        *,
        owner_id: uuid.UUID,
        filters: BotListFilters | None = None,
    ) -> int:
        stmt = self._build_owner_list_stmt(owner_id=owner_id, filters=filters).with_only_columns(
            func.count(Bot.id)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def update_bot(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
        provided_fields: set[str] | None = None,
        name: str | None = None,
        niche_id: str | None = None,
        goal_type: str | None = None,
        status: str | None = None,
        welcome_message: str | None = None,
        tone: str | None = None,
        language: str | None = None,
        short_description: str | None = None,
        provider_name: str | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> Bot | None:
        bot = await self.get_bot_by_id(owner_id=owner_id, bot_id=bot_id)
        if bot is None:
            return None

        provided = provided_fields or set()

        if "name" in provided or name is not None:
            bot.name = name
        if "niche_id" in provided or niche_id is not None:
            bot.niche_id = niche_id
        if "goal_type" in provided or goal_type is not None:
            bot.goal_type = goal_type
        if "status" in provided or status is not None:
            bot.status = status
        if "welcome_message" in provided or welcome_message is not None:
            bot.welcome_message = welcome_message
        if "tone" in provided or tone is not None:
            bot.tone = tone
        if "language" in provided or language is not None:
            bot.language = language
        if "short_description" in provided or short_description is not None:
            bot.short_description = short_description
        if "provider_name" in provided and provider_name is not None:
            bot.provider_name = provider_name
        if "model_name" in provided:
            bot.model_name = model_name
        if "temperature" in provided:
            bot.temperature = temperature
        if "max_output_tokens" in provided:
            bot.max_output_tokens = max_output_tokens

        await self._session.flush()
        await self._session.refresh(bot)
        return bot

    async def archive_bot(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> Bot | None:
        return await self.update_bot(
            owner_id=owner_id,
            bot_id=bot_id,
            status="archived",
        )

    async def delete_bot_owned(self, *, owner_id: uuid.UUID, bot_id: uuid.UUID) -> bool:
        bot = await self.get_bot_by_id(owner_id=owner_id, bot_id=bot_id)
        if bot is None:
            return False
        await self._session.delete(bot)
        await self._session.flush()
        return True

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    def _build_owner_list_stmt(
        self,
        *,
        owner_id: uuid.UUID,
        filters: BotListFilters | None,
    ) -> Select[tuple[Bot]]:
        stmt = select(Bot).where(Bot.owner_id == owner_id)
        active_filters = filters or BotListFilters()

        if not active_filters.include_archived:
            stmt = stmt.where(Bot.status != "archived")
        if active_filters.statuses:
            stmt = stmt.where(Bot.status.in_(active_filters.statuses))
        if active_filters.niche_ids:
            stmt = stmt.where(Bot.niche_id.in_(active_filters.niche_ids))
        if active_filters.goal_types:
            stmt = stmt.where(Bot.goal_type.in_(active_filters.goal_types))
        if active_filters.search:
            term = f"%{active_filters.search.strip()}%"
            if term != "%%":
                stmt = stmt.where(
                    or_(
                        Bot.name.ilike(term),
                        Bot.short_description.ilike(term),
                    )
                )
        return stmt
