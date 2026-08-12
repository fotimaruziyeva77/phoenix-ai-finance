"""Public niche catalog DTOs (``GET /api/v1/catalog/niches``)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class NicheCatalogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., min_length=1, max_length=120)
    display_name: str = Field(..., min_length=1, max_length=160)
    description: str = Field(..., max_length=2000)
    wizard_hint: str = Field(
        default="",
        max_length=500,
        description="Short line for wizard cards (may match onboarding copy).",
    )
    icon_key: str = Field(
        default="briefcase",
        max_length=64,
        description="Stable key for client-side icon mapping.",
    )
    supported_goals: list[str] = Field(
        default_factory=list,
        description="Goal types allowed when creating bots in this niche (subset of deployment goals).",
    )
    onboarding_hints: list[str] = Field(
        default_factory=list,
        description="Optional product hints for onboarding or docs.",
    )
    default_welcome_messages: dict[str, str] = Field(
        default_factory=dict,
        description="Language-keyed welcome message templates (e.g. {'en': '...', 'uz': '...'}).",
    )
    visible: bool = Field(default=True, description="When false, omitted from default catalog responses.")


class NicheCatalogResponse(BaseModel):
    """Versioned envelope so clients can branch on additive schema changes."""

    schema_version: int = Field(1, ge=1, description="Increment when removing or renaming fields.")
    niches: list[NicheCatalogItem]
