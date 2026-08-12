"""Superadmin bulk user actions endpoint."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import AdminModerationServiceDep, RequireSuperadmin, SubscriptionRepoDep, DbSession
from app.models.enums import PlanSlug
from app.services.audit_service import AuditService

router = APIRouter(prefix="/admin/users", tags=["admin-bulk"])


class BulkActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(..., pattern="^(suspend|activate|override_plan)$")
    user_ids: list[UUID] = Field(..., min_length=1, max_length=100)
    reason: str | None = Field(default=None, max_length=500)
    plan_slug: str | None = Field(default=None)  # required when action=override_plan


class BulkActionResult(BaseModel):
    user_id: UUID
    success: bool
    error: str | None = None


class BulkActionResponse(BaseModel):
    results: list[BulkActionResult]
    succeeded: int
    failed: int


@router.post(
    "/bulk-action",
    response_model=BulkActionResponse,
    summary="Bulk suspend / activate / override plan for multiple users (superadmin)",
)
async def bulk_user_action(
    body: BulkActionRequest,
    admin: RequireSuperadmin,
    svc: AdminModerationServiceDep,
    sub_repo: SubscriptionRepoDep,
    session: DbSession,
) -> BulkActionResponse:
    if body.action == "override_plan" and not body.plan_slug:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="plan_slug is required when action=override_plan.",
        )

    # Validate plan slug upfront for override_plan
    plan_slug_enum: PlanSlug | None = None
    if body.action == "override_plan":
        try:
            plan_slug_enum = PlanSlug(body.plan_slug)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown plan slug: {body.plan_slug!r}",
            )

    audit = AuditService(session)
    results: list[BulkActionResult] = []

    for uid in body.user_ids:
        try:
            if body.action == "suspend":
                result = await svc.suspend_user(
                    actor_user_id=admin.id,
                    user_id=uid,
                    reason=body.reason,
                )
                if result is None:
                    results.append(BulkActionResult(user_id=uid, success=False, error="User not found."))
                else:
                    results.append(BulkActionResult(user_id=uid, success=True))

            elif body.action == "activate":
                result = await svc.activate_user(
                    actor_user_id=admin.id,
                    user_id=uid,
                )
                if result is None:
                    results.append(BulkActionResult(user_id=uid, success=False, error="User not found."))
                else:
                    results.append(BulkActionResult(user_id=uid, success=True))

            elif body.action == "override_plan":
                assert plan_slug_enum is not None
                sub = await sub_repo.manual_override_plan(
                    user_id=uid,
                    plan_slug=plan_slug_enum,
                )
                if sub is None:
                    results.append(BulkActionResult(
                        user_id=uid, success=False,
                        error="Subscription not found for this user.",
                    ))
                else:
                    await audit.log_entity_event(
                        actor_user_id=admin.id,
                        action="subscription_plan_overridden",
                        entity_type="user",
                        entity_id=uid,
                        metadata_json={
                            "new_plan": body.plan_slug,
                            "reason": body.reason,
                        },
                    )
                    results.append(BulkActionResult(user_id=uid, success=True))

        except HTTPException as exc:
            results.append(BulkActionResult(user_id=uid, success=False, error=exc.detail))
        except Exception as exc:  # noqa: BLE001
            results.append(BulkActionResult(user_id=uid, success=False, error=str(exc)))

    # Single commit covers both moderation flushes + subscription overrides + audit
    await session.commit()

    succeeded = sum(1 for r in results if r.success)
    failed = len(results) - succeeded
    return BulkActionResponse(results=results, succeeded=succeeded, failed=failed)
