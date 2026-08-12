"""Errors for public web widget conversation/session resolution."""

from __future__ import annotations

from typing import ClassVar


class WebWidgetSessionError(Exception):
    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "web_widget_session_error"
    default_message: ClassVar[str] = "Web widget session operation failed"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class WebWidgetSessionValidationError(WebWidgetSessionError):
    status_code = 422
    code = "web_widget_session_validation_error"
    default_message = "Invalid visitor session parameters"


class WebWidgetSessionBotNotFoundError(WebWidgetSessionError):
    status_code = 404
    code = "web_widget_session_bot_not_found"
    default_message = "Bot not found"
