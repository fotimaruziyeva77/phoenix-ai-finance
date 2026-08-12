"""Unit tests for token normalization, estimation, pricing catalog merge, and cost math."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from app.ai_cost.calculator import (
    calculate_cost,
    estimate_tokens_from_messages,
    normalize_usage,
    safe_zero_usage,
)
from app.ai_cost.catalog import PricingCatalog, build_pricing_catalog
from app.ai_providers.types import ChatMessage
from app.core.config import Settings


def _settings(**extra: object) -> Settings:
    base = {
        "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
        "gemini_api_key": "k",
    }
    base.update(extra)
    return Settings.model_validate(base)


# --- 1. Total token calculation ---


def test_normalize_usage_sums_when_total_missing_or_zero() -> None:
    assert normalize_usage(3, 2, None) == (3, 2, 5)
    assert normalize_usage(3, 2, 0) == (3, 2, 5)
    assert normalize_usage(0, 7, None) == (0, 7, 7)


def test_normalize_usage_respects_explicit_total_only() -> None:
    """Provider may report only aggregate token count."""
    assert normalize_usage(None, None, 100) == (0, 0, 100)
    assert normalize_usage(0, 0, 42) == (0, 0, 42)


def test_normalize_usage_keeps_partial_fields_when_total_provided() -> None:
    """If total is non-zero we do not overwrite it with in+out (provider may disagree)."""
    inp, out, tot = normalize_usage(10, 10, 15)
    assert (inp, out, tot) == (10, 10, 15)


def test_calculate_cost_tokens_total_matches_normalize() -> None:
    cat = build_pricing_catalog(_settings())
    bd = calculate_cost(
        provider_name="gemini",
        model_name="gemini-2.5-flash",
        tokens_input=3,
        tokens_output=2,
        tokens_total=None,
        catalog=cat,
    )
    assert bd.tokens_total == 5
    assert bd.tokens_input == 3
    assert bd.tokens_output == 2


# --- 2. Cost from config ---


def test_calculate_cost_known_rates_one_million_each() -> None:
    cat = build_pricing_catalog(_settings())
    bd = calculate_cost(
        provider_name="gemini",
        model_name="gemini-2.5-flash",
        tokens_input=1_000_000,
        tokens_output=1_000_000,
        catalog=cat,
    )
    assert bd.tokens_total == 2_000_000
    assert bd.cost_usd == Decimal("0.30") + Decimal("2.50")
    assert bd.pricing_matched is True
    assert bd.used_token_estimation is False


def test_calculate_cost_fractional_million_quantized() -> None:
    cat = build_pricing_catalog(_settings())
    bd = calculate_cost(
        provider_name="gemini",
        model_name="gemini-2.5-flash",
        tokens_input=500_000,
        tokens_output=250_000,
        catalog=cat,
    )
    assert bd.cost_usd == Decimal("0.15") + Decimal("0.625")


def test_calculate_cost_unknown_model_uses_wildcard() -> None:
    cat = build_pricing_catalog(_settings())
    bd = calculate_cost(
        provider_name="gemini",
        model_name="custom-unknown",
        tokens_input=1_000_000,
        tokens_output=0,
        catalog=cat,
    )
    assert bd.cost_usd == Decimal("0.075")
    assert bd.pricing_matched is True


def test_overlay_overrides_builtin_rates() -> None:
    overlay = {
        "providers": {
            "gemini": {
                "gemini-2.5-flash": {
                    "input_usd_per_million": "1",
                    "output_usd_per_million": "2",
                }
            }
        }
    }
    cat = build_pricing_catalog(_settings(ai_pricing_json=json.dumps(overlay)))
    bd = calculate_cost(
        provider_name="gemini",
        model_name="gemini-2.5-flash",
        tokens_input=1_000_000,
        tokens_output=1_000_000,
        catalog=cat,
    )
    assert bd.cost_usd == Decimal("3")


# --- 3. Zero usage ---


def test_safe_zero_usage_all_none() -> None:
    assert safe_zero_usage(None, None, None) == (0, 0, 0)


def test_safe_zero_usage_clamps_negative() -> None:
    assert safe_zero_usage(-1, 2, -3) == (0, 2, 0)


def test_calculate_cost_zero_tokens_zero_usd_when_priced() -> None:
    cat = build_pricing_catalog(_settings())
    bd = calculate_cost(
        provider_name="gemini",
        model_name="gemini-2.5-flash",
        tokens_input=0,
        tokens_output=0,
        tokens_total=0,
        catalog=cat,
    )
    assert bd.tokens_total == 0
    assert bd.cost_usd == Decimal("0")
    assert bd.pricing_matched is True


def test_calculate_cost_total_only_zero_split_yields_zero_cost_components() -> None:
    """Total reported but no in/out split: billable line items are 0; total still tracked."""
    cat = build_pricing_catalog(_settings())
    bd = calculate_cost(
        provider_name="gemini",
        model_name="gemini-2.5-flash",
        tokens_input=0,
        tokens_output=0,
        tokens_total=10_000,
        catalog=cat,
    )
    assert bd.tokens_total == 10_000
    assert bd.cost_usd == Decimal("0")
    assert bd.pricing_matched is True


# --- 4. Invalid / partial usage ---


def test_safe_zero_usage_coerces_string_numerics() -> None:
    assert safe_zero_usage("3", "4", "10") == (3, 4, 10)  # type: ignore[arg-type]


def test_safe_zero_usage_invalid_strings_become_zero() -> None:
    assert safe_zero_usage("nope", None, None) == (0, 0, 0)  # type: ignore[arg-type]
    assert safe_zero_usage([], {}, None) == (0, 0, 0)  # type: ignore[arg-type]


def test_calculate_cost_unknown_provider_tokens_still_normalized() -> None:
    cat = build_pricing_catalog(_settings())
    bd = calculate_cost(
        provider_name="openai",
        model_name="gpt-4",
        tokens_input=100,
        tokens_output=100,
        catalog=cat,
    )
    assert bd.cost_usd is None
    assert bd.pricing_matched is False
    assert bd.tokens_total == 200


def test_resolve_strips_whitespace_provider_and_model() -> None:
    cat = build_pricing_catalog(_settings())
    bd = calculate_cost(
        provider_name="  Gemini ",
        model_name="  gemini-2.5-flash  ",
        tokens_input=1_000_000,
        tokens_output=0,
        catalog=cat,
    )
    assert bd.cost_usd == Decimal("0.30")
    assert bd.pricing_matched is True


def test_resolve_empty_provider_no_match() -> None:
    cat = build_pricing_catalog(_settings())
    bd = calculate_cost(
        provider_name="",
        model_name="gemini-2.5-flash",
        tokens_input=100,
        tokens_output=0,
        catalog=cat,
    )
    assert bd.cost_usd is None
    assert bd.pricing_matched is False


def test_invalid_pricing_json_raises() -> None:
    with pytest.raises(ValueError, match="Invalid AI_PRICING_JSON"):
        build_pricing_catalog(_settings(ai_pricing_json="not json"))


def test_pricing_json_non_object_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid AI_PRICING_JSON"):
        build_pricing_catalog(_settings(ai_pricing_json=json.dumps([1, 2])))


# --- 5. Extensibility (new provider / model via config only) ---


def test_overlay_adds_new_provider_without_code_change() -> None:
    overlay = {
        "providers": {
            "openai": {
                "gpt-5": {
                    "input_usd_per_million": "0.5",
                    "output_usd_per_million": "1.5",
                }
            }
        }
    }
    cat = build_pricing_catalog(_settings(ai_pricing_json=json.dumps(overlay)))
    assert isinstance(cat, PricingCatalog)
    bd = calculate_cost(
        provider_name="openai",
        model_name="gpt-5",
        tokens_input=2_000_000,
        tokens_output=1_000_000,
        catalog=cat,
    )
    assert bd.cost_usd == Decimal("1.0") + Decimal("1.5")
    assert "openai" in cat.providers


def test_overlay_adds_model_under_existing_provider() -> None:
    overlay = {
        "providers": {
            "gemini": {
                "future-gemini-x": {
                    "input_usd_per_million": "0.01",
                    "output_usd_per_million": "0.02",
                }
            }
        }
    }
    cat = build_pricing_catalog(_settings(ai_pricing_json=json.dumps(overlay)))
    bd = calculate_cost(
        provider_name="gemini",
        model_name="future-gemini-x",
        tokens_input=1_000_000,
        tokens_output=1_000_000,
        catalog=cat,
    )
    assert bd.cost_usd == Decimal("0.03")


# --- Estimation helper ---


def test_estimate_tokens_from_messages() -> None:
    msgs = (
        ChatMessage(role="system", content="abcd"),
        ChatMessage(role="user", content="efgh"),
    )
    inp, out = estimate_tokens_from_messages(
        messages=msgs, completion_text="ijkl", chars_per_token=4.0
    )
    assert inp == 2
    assert out == 1


def test_estimate_tokens_empty_yields_zero() -> None:
    assert estimate_tokens_from_messages(
        messages=(), completion_text="", chars_per_token=4.0
    ) == (0, 0)
