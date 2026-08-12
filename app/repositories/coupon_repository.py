"""CRUD repository for Coupon."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coupon import Coupon


class CouponRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Coupon]:
        result = await self._session.execute(
            select(Coupon).order_by(Coupon.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, coupon_id: uuid.UUID) -> Coupon | None:
        result = await self._session.execute(
            select(Coupon).where(Coupon.id == coupon_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Coupon | None:
        result = await self._session.execute(
            select(Coupon).where(Coupon.code == code.strip().upper())
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        code: str,
        discount_type: str,
        discount_value: Decimal,
        target_plan: str | None,
        max_uses: int | None,
        expires_at: datetime | None,
        created_by_id: uuid.UUID,
    ) -> Coupon:
        coupon = Coupon(
            code=code.strip().upper(),
            discount_type=discount_type,
            discount_value=discount_value,
            target_plan=target_plan or None,
            max_uses=max_uses,
            expires_at=expires_at,
            created_by_id=created_by_id,
        )
        self._session.add(coupon)
        await self._session.flush()
        return coupon

    async def update(
        self,
        coupon: Coupon,
        *,
        is_active: bool | None = None,
        max_uses: int | None = None,
        expires_at: datetime | None = None,
        clear_expires: bool = False,
    ) -> Coupon:
        if is_active is not None:
            coupon.is_active = is_active
        if max_uses is not None:
            coupon.max_uses = max_uses
        if clear_expires:
            coupon.expires_at = None
        elif expires_at is not None:
            coupon.expires_at = expires_at
        return coupon

    async def increment_used(self, coupon: Coupon) -> Coupon:
        coupon.used_count = (coupon.used_count or 0) + 1
        return coupon

    async def delete(self, coupon: Coupon) -> None:
        await self._session.delete(coupon)

    def is_valid(self, coupon: Coupon) -> bool:
        """Check if coupon can still be redeemed."""
        if not coupon.is_active:
            return False
        if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
            return False
        if coupon.expires_at and coupon.expires_at < datetime.now(UTC):
            return False
        return True

    async def commit(self) -> None:
        await self._session.commit()
