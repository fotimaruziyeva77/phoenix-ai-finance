"""Platform administration API (superadmin only). Owner-scoped product APIs stay under ``/bots``, etc."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import RequireSuperadmin

router = APIRouter(prefix="/admin/platform", tags=["admin-platform"])


@router.get(
    "/session",
    summary="Confirm superadmin session",
    description=(
        "Minimal endpoint to verify JWT + DB role for platform operators. "
        "Tenant data remains under owner-scoped routes; cross-tenant listings belong in future "
        "handlers that check :class:`~app.core.rbac.PlatformCapability`."
    ),
)
async def admin_platform_session(user: RequireSuperadmin) -> dict[str, str]:
    return {"user_id": str(user.id), "role": user.role.value}
