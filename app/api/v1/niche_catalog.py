"""Public read-only catalog endpoints (no auth; safe for marketing + dashboard)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.lib.niche_registry import NicheDefinition, list_visible_niche_definitions
from app.schemas.niche_catalog import NicheCatalogItem, NicheCatalogResponse

router = APIRouter(tags=["catalog"])

_CATALOG_CACHE_CONTROL = "public, max-age=3600, stale-while-revalidate=600"


def _to_catalog_item(n: NicheDefinition) -> NicheCatalogItem:
    return NicheCatalogItem(
        id=n.id,
        display_name=n.label,
        description=n.short_description,
        wizard_hint=n.wizard_hint,
        icon_key=n.icon_key,
        supported_goals=list(n.supported_goals),
        onboarding_hints=list(n.onboarding_hints),
        default_welcome_messages=dict(n.default_welcome_messages),
        visible=n.visible,
    )


@router.get(
    "/catalog/niches",
    response_model=NicheCatalogResponse,
    summary="Supported bot niches (metadata)",
    description=(
        "Canonical niche list for onboarding and display. "
        "``schema_version`` bumps only on breaking JSON shape changes; new fields are additive."
    ),
)
async def get_niche_catalog() -> JSONResponse:
    items = [_to_catalog_item(n) for n in list_visible_niche_definitions()]
    body = NicheCatalogResponse(schema_version=1, niches=items)
    return JSONResponse(
        content=body.model_dump(mode="json"),
        headers={"Cache-Control": _CATALOG_CACHE_CONTROL},
    )
