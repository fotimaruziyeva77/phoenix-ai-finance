"""Superadmin coupon/promo code management."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CouponRepoDep, DbSession, RequireSuperadmin
from app.schemas.coupons import (
    CouponCreate,
    CouponListResponse,
    CouponRead,
    CouponUpdate,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/admin/coupons", tags=["admin-coupons"])


def _to_read(c) -> CouponRead:
    return CouponRead(
        id=c.id, code=c.code,
        discount_type=c.discount_type,
        discount_value=Decimal(str(c.discount_value)),
        target_plan=c.target_plan,
        max_uses=c.max_uses, used_count=c.used_count,
        is_active=c.is_active, expires_at=c.expires_at,
        created_by_id=c.created_by_id,
        created_at=c.created_at, updated_at=c.updated_at,
    )


@router.get("", response_model=CouponListResponse, summary="List all coupons (superadmin)")
async def list_coupons(
    _admin: RequireSuperadmin,
    repo: CouponRepoDep,
) -> CouponListResponse:
    coupons = await repo.list_all()
    return CouponListResponse(items=[_to_read(c) for c in coupons], total=len(coupons))


@router.post(
    "", response_model=CouponRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a coupon (superadmin)",
)
async def create_coupon(
    body: CouponCreate,
    admin: RequireSuperadmin,
    repo: CouponRepoDep,
    session: DbSession,
) -> CouponRead:
    existing = await repo.get_by_code(body.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Coupon with code {body.code!r} already exists.",
        )
    coupon = await repo.create(
        code=body.code,
        discount_type=body.discount_type,
        discount_value=body.discount_value,
        target_plan=body.target_plan,
        max_uses=body.max_uses,
        expires_at=body.expires_at,
        created_by_id=admin.id,
    )

    audit = AuditService(session)
    await audit.log_entity_event(
        actor_user_id=admin.id,
        action="coupon_created",
        entity_type="coupon",
        entity_id=coupon.id,
        after_snapshot={
            "code": body.code,
            "discount_type": body.discount_type,
            "discount_value": str(body.discount_value),
            "target_plan": body.target_plan,
            "max_uses": body.max_uses,
        },
    )
    await repo.commit()
    refreshed = await repo.get_by_id(coupon.id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Coupon disappeared after create.")
    return _to_read(refreshed)


@router.patch(
    "/{coupon_id}", response_model=CouponRead,
    summary="Update a coupon (superadmin)",
)
async def update_coupon(
    coupon_id: UUID,
    body: CouponUpdate,
    admin: RequireSuperadmin,
    repo: CouponRepoDep,
    session: DbSession,
) -> CouponRead:
    coupon = await repo.get_by_id(coupon_id)
    if coupon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found.")

    before = {
        "is_active": coupon.is_active,
        "max_uses": coupon.max_uses,
        "expires_at": coupon.expires_at.isoformat() if coupon.expires_at else None,
    }
    await repo.update(
        coupon,
        is_active=body.is_active,
        max_uses=body.max_uses,
        expires_at=body.expires_at,
        clear_expires=body.clear_expires,
    )

    audit = AuditService(session)
    await audit.log_entity_event(
        actor_user_id=admin.id,
        action="coupon_updated",
        entity_type="coupon",
        entity_id=coupon_id,
        before_snapshot=before,
        after_snapshot={
            "is_active": body.is_active,
            "max_uses": body.max_uses,
        },
    )
    await repo.commit()
    refreshed = await repo.get_by_id(coupon_id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Coupon disappeared after update.")
    return _to_read(refreshed)


@router.delete(
    "/{coupon_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a coupon (superadmin)",
)
async def delete_coupon(
    coupon_id: UUID,
    admin: RequireSuperadmin,
    repo: CouponRepoDep,
    session: DbSession,
) -> None:
    coupon = await repo.get_by_id(coupon_id)
    if coupon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found.")

    audit = AuditService(session)
    await audit.log_entity_event(
        actor_user_id=admin.id,
        action="coupon_deleted",
        entity_type="coupon",
        entity_id=coupon_id,
        before_snapshot={"code": coupon.code, "used_count": coupon.used_count},
    )
    await repo.delete(coupon)
    await repo.commit()
