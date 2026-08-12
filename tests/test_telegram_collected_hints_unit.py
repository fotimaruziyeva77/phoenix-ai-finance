"""Unit tests for :mod:`app.lib.telegram_collected_hints`."""

from __future__ import annotations

from app.lib.telegram_collected_hints import merge_telegram_sender_into_collected


def test_merge_adds_username_and_first_name_and_seeds_full_name_when_missing() -> None:
    data, changed = merge_telegram_sender_into_collected(
        {},
        from_username="alex_u",
        from_first_name="Alex",
    )
    assert changed
    assert data["telegram_username"] == "alex_u"
    assert data["telegram_first_name"] == "Alex"
    assert data["full_name"] == "Alex"


def test_merge_does_not_overwrite_existing_name_slots() -> None:
    data, changed = merge_telegram_sender_into_collected(
        {"full_name": "Jordan P"},
        from_username="jp",
        from_first_name="TelegramFirst",
    )
    assert changed
    assert data["full_name"] == "Jordan P"
    assert data["telegram_username"] == "jp"
    assert data["telegram_first_name"] == "TelegramFirst"


def test_merge_idempotent_for_same_keys() -> None:
    base = {"telegram_username": "u1", "telegram_first_name": "N", "full_name": "N"}
    data, changed = merge_telegram_sender_into_collected(
        base,
        from_username="other",
        from_first_name="Other",
    )
    assert not changed
    assert data == base


def test_merge_empty_sender_noop() -> None:
    data, changed = merge_telegram_sender_into_collected(
        {"phone": "+1"},
        from_username=None,
        from_first_name="  ",
    )
    assert not changed


def test_merge_treats_non_object_json_as_empty_base() -> None:
    data, changed = merge_telegram_sender_into_collected(
        [],  # type: ignore[arg-type]
        from_username="u",
        from_first_name="U",
    )
    assert changed
    assert data == {
        "telegram_username": "u",
        "telegram_first_name": "U",
        "full_name": "U",
    }


def test_merge_list_of_strings_does_not_crash() -> None:
    data, changed = merge_telegram_sender_into_collected(
        ["a", "b"],  # type: ignore[arg-type]
        from_username="x",
        from_first_name=None,
    )
    assert changed
    assert data == {"telegram_username": "x"}
