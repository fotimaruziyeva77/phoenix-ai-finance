"""Stable ``revoke_reason`` values for :class:`~app.models.refresh_session.RefreshSession`."""

from __future__ import annotations

REVOKE_REASON_ROTATED = "rotated"
REVOKE_REASON_LOGOUT = "logout"
REVOKE_REASON_LOGOUT_ALL = "logout_all"
REVOKE_REASON_FAMILY_INVALIDATED = "family_invalidated"
REVOKE_REASON_REUSE_DETECTED = "reuse_detected"
