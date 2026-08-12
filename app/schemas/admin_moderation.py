"""Request bodies for superadmin moderation actions."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AdminModerationReasonBody(BaseModel):
    """Optional internal note stored on the user/bot row and copied into audit metadata."""

    reason: str | None = Field(default=None, max_length=1024)
