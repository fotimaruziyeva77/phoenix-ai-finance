"""Unit tests for :mod:`app.core.ai_generation_policy`."""

from app.core.ai_generation_policy import clamp_small_completion_budget, resolve_max_output_tokens


def test_resolve_max_output_tokens_uses_default_when_bot_unset() -> None:
    assert (
        resolve_max_output_tokens(
            bot_max_output_tokens=None,
            ceiling=8192,
            default_when_unset=4096,
        )
        == 4096
    )


def test_resolve_max_output_tokens_clamps_bot_above_ceiling() -> None:
    assert (
        resolve_max_output_tokens(
            bot_max_output_tokens=100_000,
            ceiling=8192,
            default_when_unset=4096,
        )
        == 8192
    )


def test_resolve_max_output_tokens_raises_floor() -> None:
    assert (
        resolve_max_output_tokens(
            bot_max_output_tokens=10,
            ceiling=8192,
            default_when_unset=4096,
            floor=256,
        )
        == 256
    )


def test_clamp_small_completion_budget() -> None:
    assert clamp_small_completion_budget(128, ceiling=8192, floor=32) == 128
    assert clamp_small_completion_budget(128, ceiling=64, floor=32) == 64
