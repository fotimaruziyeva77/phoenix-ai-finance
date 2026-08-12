"""Superadmin read-only tenant inspection (audited)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import RequireSuperadmin, TenantInspectionServiceDep
from app.schemas.platform_admin import AdminTenantInspectionResponse

router = APIRouter(prefix="/admin", tags=["admin-tenant-inspection"])


@router.get(
    "/tenants/{owner_user_id}/inspection",
    response_model=AdminTenantInspectionResponse,
    summary="Inspect tenant (read-only, superadmin, audited)",
)
async def admin_inspect_tenant(
    owner_user_id: UUID,
    _admin: RequireSuperadmin,
    svc: TenantInspectionServiceDep,
) -> AdminTenantInspectionResponse:
    row = await svc.inspect_tenant(actor_user_id=_admin.id, owner_user_id=owner_user_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant user not found.")
    return row
