"""Merge env pricing overlay with defaults; resolve rates per provider + model."""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from decimal import Decimal
from typing import Any

from app.ai_cost.defaults import DEFAULT_RATES_BY_PROVIDER
from app.ai_cost.pricing_config import ModelRateConfig, PricingOverlayConfig
from app.core.config import Settings


def _deep_copy_decimal_map(
    src: dict[str, dict[str, tuple[Decimal, Decimal]]],
) -> dict[str, dict[str, tuple[Decimal, Decimal]]]:
    return deepcopy(src)


def _overlay_merge(
    base: dict[str, dict[str, tuple[Decimal, Decimal]]],
    overlay: dict[str, dict[str, ModelRateConfig]],
) -> None:
    for prov, models in overlay.items():
        pk = prov.strip().lower()
        if pk not in base:
            base[pk] = {}
        for mid, cfg in models.items():
            key = mid.strip()
            base[pk][key] = (cfg.input_usd_per_million, cfg.output_usd_per_million)


def build_pricing_catalog(settings: Settings) -> PricingCatalog:
    """
    Build a catalog from :mod:`app.ai_cost.defaults` plus optional JSON overlay.

    Overlay env: ``APP_AI_PRICING_JSON`` or ``AI_PRICING_JSON`` (see :class:`~app.core.config.Settings`).
    """
    merged = _deep_copy_decimal_map(DEFAULT_RATES_BY_PROVIDER)
    raw = settings.ai_pricing_json
    if raw and str(raw).strip():
        try:
            data: Any = json.loads(str(raw))
            if not isinstance(data, dict):
                raise ValueError("pricing JSON must be an object")
            overlay = PricingOverlayConfig.model_validate(data)
            _overlay_merge(merged, overlay.providers)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"Invalid AI_PRICING_JSON: {exc}") from exc
    return PricingCatalog(merged)


class PricingCatalog:
    __slots__ = ("_rates",)

    def __init__(self, rates: dict[str, dict[str, tuple[Decimal, Decimal]]]) -> None:
        self._rates = rates

    def resolve_usd_per_million(
        self,
        *,
        provider_name: str,
        model_name: str,
    ) -> tuple[Decimal, Decimal] | None:
        pk = (provider_name or "").strip().lower()
        if not pk:
            return None
        models = self._rates.get(pk)
        if not models:
            return None
        mid = (model_name or "").strip()
        if mid in models:
            return models[mid]
        if "*" in models:
            return models["*"]
        return None

    @property
    def providers(self) -> Mapping[str, Mapping[str, tuple[Decimal, Decimal]]]:
        return self._rates
