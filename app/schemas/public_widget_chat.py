"""Public (unauthenticated) widget chat HTTP contract."""

from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PublicWidgetChatRequest(BaseModel):
    """Send a visitor turn; omit ``conversation_id`` on first contact for a given ``visitor_session_key``."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        ...,
        min_length=1,
        max_length=32000,
        description="Visitor message (trimmed server-side).",
    )
    visitor_session_key: str | None = Field(
        default=None,
        description="Opaque id from a prior response; omit to start a new thread (server issues a key).",
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Continue this thread; must pair with the same ``visitor_session_key`` used to open it.",
    )

    @model_validator(mode="after")
    def _conversation_requires_visitor_key(self) -> Self:
        if self.conversation_id is None:
            return self
        if not (self.visitor_session_key or "").strip():
            raise ValueError("visitor_session_key is required when conversation_id is provided")
        return self


class PublicWidgetChatResponse(BaseModel):
    """Assistant reply and thread handles for the next request (no owner or billing internals)."""

    model_config = ConfigDict(from_attributes=True)

    conversation_id: UUID
    visitor_session_key: str = Field(description="Persist client-side; send back on the next turn.")
    user_message_id: UUID
    assistant_message_id: UUID = Field(description="Assistant row id for this reply.")
    assistant_text: str
    bot_display_name: str = Field(max_length=160, description="Public bot title (same as bootstrap).")
