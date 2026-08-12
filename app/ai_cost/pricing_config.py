"""Pydantic shapes for ``APP_AI_PRICING_JSON`` / ``AI_PRICING_JSON``."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class ModelRateConfig(BaseModel):
    """USD per 1_000_000 tokens (industry-standard list pricing units)."""

    input_usd_per_million: Decimal = Field(..., ge=0)
    output_usd_per_million: Decimal = Field(..., ge=0)

    @field_validator("input_usd_per_million", "output_usd_per_million", mode="before")
    @classmethod
    def coerce_decimal(cls, v: object) -> object:
        if v is None:
            raise ValueError("rate cannot be null")
        return v


class PricingOverlayConfig(BaseModel):
    """Root JSON object merged on top of built-in defaults."""

    providers: dict[str, dict[str, ModelRateConfig]] = Field(default_factory=dict)
