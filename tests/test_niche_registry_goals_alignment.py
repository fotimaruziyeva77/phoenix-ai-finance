"""Niche registry goals must remain a subset of bot API goal types."""

from __future__ import annotations

from app.lib.niche_registry import STANDARD_BOT_GOAL_TYPES, list_supported_niches
from app.schemas.bots import ALLOWED_GOAL_TYPES


def test_standard_bot_goal_types_match_schema() -> None:
    assert tuple(ALLOWED_GOAL_TYPES) == STANDARD_BOT_GOAL_TYPES


def test_each_niche_supported_goals_are_allowed() -> None:
    allowed = set(ALLOWED_GOAL_TYPES)
    for n in list_supported_niches():
        for g in n.supported_goals:
            assert g in allowed
