"""Superadmin user impersonation (short-lived token, audited)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import PlatformAdminRepoDep, RequireSuperadmin
from app.core.rbac import is_superadmin
from app.core.security import create_impersonation_token
from app.services.audit_service import AuditService
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.core.db import get_db
from typing import Annotated

router = APIRouter(prefix="/admin/users", tags=["admin-impersonation"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


class ImpersonationResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes
    target_user_id: UUID
    target_email: str


@router.post(
    "/{user_id}/impersonate",
    response_model=ImpersonationResponse,
    summary="Generate a 15-min impersonation token for a user (superadmin only)",
)
async def impersonate_user(
    user_id: UUID,
    admin: RequireSuperadmin,
    repo: PlatformAdminRepoDep,
    session: DbSession,
) -> ImpersonationResponse:
    target = await repo.get_user_with_oauth(user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if is_superadmin(target):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot impersonate a superadmin account.",
        )

    token = create_impersonation_token(
        target_user_id=target.id,
        target_role=target.role.value,
        target_email=target.email,
        impersonated_by=admin.id,
    )

    # Audit log the impersonation event
    audit = AuditService(session)
    await audit.log_entity_event(
        actor_user_id=admin.id,
        action="user_impersonated",
        entity_type="user",
        entity_id=target.id,
        before_snapshot=None,
        after_snapshot=None,
        metadata_json={"impersonated_by": str(admin.id), "target_email": target.email},
    )
    await session.commit()

    return ImpersonationResponse(
        access_token=token,
        target_user_id=target.id,
        target_email=target.email,
    )
