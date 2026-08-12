from fastapi import APIRouter

from app.services.health_service import get_public_health

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return await get_public_health()
