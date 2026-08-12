"""GitHub email selection (verified-only, hidden public email)."""

from __future__ import annotations

from app.integrations.github_idp import pick_verified_login_email


def test_pick_primary_verified_email() -> None:
    user: dict = {"email": None}
    emails = [
        {"email": "secondary@x.com", "primary": False, "verified": True},
        {"email": "primary@x.com", "primary": True, "verified": True},
    ]
    assert pick_verified_login_email(user, emails) == "primary@x.com"


def test_pick_any_verified_when_no_primary_flag() -> None:
    user: dict = {"email": None}
    emails = [{"email": "only@x.com", "primary": False, "verified": True}]
    assert pick_verified_login_email(user, emails) == "only@x.com"


def test_profile_email_without_verified_api_rows_rejected() -> None:
    """If the emails API returns nothing, do not trust ``user.email`` alone."""
    user = {"email": "solo@x.com"}
    assert pick_verified_login_email(user, []) is None


def test_public_email_ok_when_verified_row_matches_case_insensitive() -> None:
    user = {"email": "Same@x.com"}
    emails = [{"email": "same@x.com", "primary": True, "verified": True}]
    assert pick_verified_login_email(user, emails) == "same@x.com"


def test_unverified_emails_rejected() -> None:
    user: dict = {"email": None}
    emails = [{"email": "nope@x.com", "primary": True, "verified": False}]
    assert pick_verified_login_email(user, emails) is None
