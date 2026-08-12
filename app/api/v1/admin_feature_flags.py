"""Superadmin CRUD for feature flags — runtime toggles without deploys."""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, FeatureFlagRepoDep, RequireSuperadmin
from app.models.user import User
from app.schemas.feature_flags import (
    FeatureFlagCreate,
    FeatureFlagListResponse,
    FeatureFlagRead,
    FeatureFlagUpdate,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/admin/feature-flags", tags=["admin-feature-flags"])


async def _resolve_emails_to_ids(session: AsyncSession, emails: list[str]) -> str | None:
    """Resolve user emails to a JSON string of UUIDs."""
    result = await session.execute(
        select(User.id).where(User.email.in_(emails))
    )
    ids = [str(row[0]) for row in result.all()]
    return json.dumps(ids) if ids else None


async def _resolve_ids_to_emails(session: AsyncSession, ids_json: str | None) -> list[str] | None:
    """Resolve a JSON string of UUIDs back to user emails."""
    if not ids_json:
        return None
    try:
        ids = json.loads(ids_json)
    except (json.JSONDecodeError, TypeError):
        return None
    if not ids:
        return None
    result = await session.execute(
        select(User.email).where(User.id.in_(ids))
    )
    return [row[0] for row in result.all()] or None


def _parse_target_user_ids(raw: str | None) -> list[str] | None:
    """Parse the JSON column value into a list of UUID strings."""
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if parsed else None
    except (json.JSONDecodeError, TypeError):
        return None


async def _to_read(flag, session: AsyncSession) -> FeatureFlagRead:
    target_user_ids = _parse_target_user_ids(flag.target_user_ids)
    target_user_emails = await _resolve_ids_to_emails(session, flag.target_user_ids)
    return FeatureFlagRead(
        id=flag.id,
        key=flag.key,
        is_enabled=flag.is_enabled,
        target_plan=flag.target_plan,
        target_user_ids=target_user_ids,
        target_user_emails=target_user_emails,
        description=flag.description,
        updated_by_id=flag.updated_by_id,
        created_at=flag.created_at,
        updated_at=flag.updated_at,
    )


@router.get(
    "",
    response_model=FeatureFlagListResponse,
    summary="List all feature flags (superadmin)",
)
async def list_feature_flags(
    _admin: RequireSuperadmin,
    repo: FeatureFlagRepoDep,
    session: DbSession,
) -> FeatureFlagListResponse:
    flags = await repo.list_all()
    items = [await _to_read(f, session) for f in flags]
    return FeatureFlagListResponse(
        items=items,
        total=len(flags),
    )


@router.post(
    "",
    response_model=FeatureFlagRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a feature flag (superadmin)",
)
async def create_feature_flag(
    body: FeatureFlagCreate,
    admin: RequireSuperadmin,
    repo: FeatureFlagRepoDep,
    session: DbSession,
) -> FeatureFlagRead:
    existing = await repo.get_by_key(body.key)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Feature flag with key {body.key!r} already exists.",
        )

    target_user_ids: str | None = None
    if body.target_user_emails:
        target_user_ids = await _resolve_emails_to_ids(session, body.target_user_emails)

    flag = await repo.create(
        key=body.key,
        description=body.description,
        is_enabled=body.is_enabled,
        target_plan=body.target_plan,
        target_user_ids=target_user_ids,
        created_by_id=admin.id,
    )

    audit = AuditService(session)
    await audit.log_entity_event(
        actor_user_id=admin.id,
        action="feature_flag_created",
        entity_type="feature_flag",
        entity_id=flag.id,
        after_snapshot={
            "key": body.key,
            "is_enabled": body.is_enabled,
            "target_plan": body.target_plan,
            "target_user_emails": body.target_user_emails,
        },
    )
    await repo.commit()
    refreshed = await repo.get_by_id(flag.id)
    if refreshed is None:
        raise HTTPException(status_code=500, detail="Flag disappeared after create.")
    return await _to_read(refreshed, session)


@router.patch(
    "/{flag_id}",
    response_model=FeatureFlagRead,
    summary="Update a feature flag (superadmin)",
)
async def update_feature_flag(
    flag_id: UUID,
    body: FeatureFlagUpdate,
    admin: RequireSuperadmin,
    repo: FeatureFlagRepoDep,
    session: DbSession,
) -> FeatureFlagRead:
    flag = await repo.get_by_id(flag_id)
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found.")

    target_user_ids: str | None = None
    if body.target_user_emails:
        target_user_ids = await _resolve_emails_to_ids(session, body.target_user_emails)

    before = {"key": flag.key, "is_enabled": flag.is_enabled, "target_plan": flag.target_plan}
    await repo.update(
        flag,
        is_enabled=body.is_enabled,
        description=body.description,
        target_plan=body.target_plan,
        clear_target_plan=body.clear_target_plan,
        target_user_ids=target_user_ids,
        clear_target_users=body.clear_target_users,
        updated_by_id=admin.id,
    )

    audit = AuditService(session)
    await audit.log_entity_event(
        actor_user_id=admin.id,
        action="feature_flag_updated",
        entity_type="feature_flag",
        entity_id=flag_id,
        before_snapshot=before,
        after_snapshot={
            "is_enabled": body.is_enabled,
            "target_plan": body.target_plan,
            "target_user_emails": body.target_user_emails,
        },
    )
    await repo.commit()
    refreshed = await repo.get_by_id(flag.id)
    if refreshed is None:
        raise HTTPException(status_code=500, detail="Flag disappeared after update.")
    return await _to_read(refreshed, session)


@router.delete(
    "/{flag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a feature flag (superadmin)",
)
async def delete_feature_flag(
    flag_id: UUID,
    admin: RequireSuperadmin,
    repo: FeatureFlagRepoDep,
    session: DbSession,
) -> None:
    flag = await repo.get_by_id(flag_id)
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found.")

    audit = AuditService(session)
    await audit.log_entity_event(
        actor_user_id=admin.id,
        action="feature_flag_deleted",
        entity_type="feature_flag",
        entity_id=flag_id,
        before_snapshot={"key": flag.key, "is_enabled": flag.is_enabled},
    )
    await repo.delete(flag)
    await repo.commit()
