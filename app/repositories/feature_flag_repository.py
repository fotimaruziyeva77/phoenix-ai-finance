"""CRUD repository for FeatureFlag admin management."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feature_flag import FeatureFlag


class FeatureFlagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[FeatureFlag]:
        result = await self._session.execute(
            select(FeatureFlag).order_by(FeatureFlag.key)
        )
        return list(result.scalars().all())

    async def get_by_id(self, flag_id: uuid.UUID) -> FeatureFlag | None:
        result = await self._session.execute(
            select(FeatureFlag).where(FeatureFlag.id == flag_id)
        )
        return result.scalar_one_or_none()

    async def get_by_key(self, key: str) -> FeatureFlag | None:
        result = await self._session.execute(
            select(FeatureFlag).where(FeatureFlag.key == key)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        key: str,
        description: str | None,
        is_enabled: bool,
        target_plan: str | None,
        target_user_ids: str | None = None,
        created_by_id: uuid.UUID,
    ) -> FeatureFlag:
        flag = FeatureFlag(
            key=key.strip().lower(),
            description=description,
            is_enabled=is_enabled,
            target_plan=target_plan or None,
            target_user_ids=target_user_ids,
            updated_by_id=created_by_id,
        )
        self._session.add(flag)
        await self._session.flush()
        return flag

    async def update(
        self,
        flag: FeatureFlag,
        *,
        is_enabled: bool | None = None,
        description: str | None = None,
        target_plan: str | None = None,
        clear_target_plan: bool = False,
        target_user_ids: str | None = None,
        clear_target_users: bool = False,
        updated_by_id: uuid.UUID | None = None,
    ) -> FeatureFlag:
        if is_enabled is not None:
            flag.is_enabled = is_enabled
        if description is not None:
            flag.description = description
        if clear_target_plan:
            flag.target_plan = None
        elif target_plan is not None:
            flag.target_plan = target_plan
        if clear_target_users:
            flag.target_user_ids = None
        elif target_user_ids is not None:
            flag.target_user_ids = target_user_ids
        if updated_by_id is not None:
            flag.updated_by_id = updated_by_id
        return flag

    async def delete(self, flag: FeatureFlag) -> None:
        await self._session.delete(flag)

    async def commit(self) -> None:
        await self._session.commit()
