"""Pydantic validation for bot AI settings (no DB)."""

from __future__ import annotations

import pytest
from app.schemas.bots import BotCreate, BotUpdate
from pydantic import ValidationError


def test_bot_create_accepts_default_provider_and_optional_sampling() -> None:
    b = BotCreate(
        name="X",
        niche_id="education",
        goal_type="support",
        model_name="gemini-2.5-flash",
        temperature=0.7,
        max_output_tokens=512,
    )
    assert b.provider_name == "gemini"
    assert b.model_name == "gemini-2.5-flash"
    assert b.temperature == 0.7
    assert b.max_output_tokens == 512


def test_bot_create_rejects_unknown_provider() -> None:
    with pytest.raises(ValidationError):
        BotCreate(name="X", niche_id="education", goal_type="support", provider_name="unknown_vendor")


def test_bot_create_rejects_invalid_model_id() -> None:
    with pytest.raises(ValidationError):
        BotCreate(name="X", niche_id="education", goal_type="support", model_name="../../etc/passwd")


def test_bot_update_allows_clearing_optional_sampling_with_null() -> None:
    u = BotUpdate.model_validate({"temperature": None, "max_output_tokens": None, "model_name": None})
    assert u.temperature is None
    assert u.max_output_tokens is None
    assert u.model_name is None


def test_bot_create_rejects_temperature_out_of_range() -> None:
    with pytest.raises(ValidationError):
        BotCreate(
            name="X",
            niche_id="education",
            goal_type="support",
            temperature=2.01,
        )


def test_bot_create_rejects_max_output_tokens_out_of_range() -> None:
    with pytest.raises(ValidationError):
        BotCreate(
            name="X",
            niche_id="education",
            goal_type="support",
            max_output_tokens=9000,
        )
    with pytest.raises(ValidationError):
        BotCreate(
            name="X",
            niche_id="education",
            goal_type="support",
            max_output_tokens=0,
        )


def test_bot_update_rejects_invalid_temperature_via_fastapi_shape() -> None:
    with pytest.raises(ValidationError):
        BotUpdate.model_validate({"temperature": -0.1})


def test_bot_create_initial_channel_web_rejects_telegram_token() -> None:
    with pytest.raises(ValidationError):
        BotCreate(
            name="X",
            niche_id="education",
            goal_type="support",
            initial_channel="web",
            telegram_bot_token="1234567890:AA_some_token_here",
        )


def test_bot_create_telegram_token_requires_initial_channel() -> None:
    with pytest.raises(ValidationError):
        BotCreate(
            name="X",
            niche_id="education",
            goal_type="support",
            telegram_bot_token="1234567890:AA_some_token_here",
        )


def test_bot_update_accepts_channel_pending_status() -> None:
    u = BotUpdate.model_validate({"status": "channel_pending"})
    assert u.status == "channel_pending"
