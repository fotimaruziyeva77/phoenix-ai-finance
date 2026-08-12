"""Errors specific to public widget chat (conversation binding)."""

from __future__ import annotations

from typing import ClassVar


class PublicWidgetChatError(Exception):
    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "public_widget_chat_error"
    default_message: ClassVar[str] = "Public widget chat failed"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class PublicWidgetChatConversationBindingError(PublicWidgetChatError):
    """``conversation_id`` does not match visitor session or is not a web_widget thread."""

    status_code = 403
    code = "public_widget_conversation_mismatch"
    default_message = "Conversation does not match this visitor session."


class PublicWidgetChatUnavailableError(PublicWidgetChatError):
    """Rare misconfiguration (e.g. owner row missing); generic message for visitors."""

    status_code = 503
    code = "public_widget_chat_unavailable"
    default_message = "Service temporarily unavailable."


class PublicWidgetChatBotSuspendedError(PublicWidgetChatError):
    """Platform-suspended bot; no AI processing for public widget."""

    status_code = 403
    code = "public_widget_bot_suspended"
    default_message = "This assistant is not available."
