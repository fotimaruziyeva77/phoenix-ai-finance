"""Domain errors for widget configuration (owner dashboard flows)."""

from __future__ import annotations

from typing import ClassVar


class WidgetConfigServiceError(Exception):
    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "widget_config_error"
    default_message: ClassVar[str] = "Widget configuration operation failed"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class WidgetConfigValidationError(WidgetConfigServiceError):
    status_code = 422
    code = "widget_config_validation_error"
    default_message = "Widget configuration payload is invalid"


class WidgetConfigNotFoundError(WidgetConfigServiceError):
    status_code = 404
    code = "widget_config_not_found"
    default_message = "Widget is not configured for this bot"


class WidgetConfigPersistenceError(WidgetConfigServiceError):
    status_code = 500
    code = "widget_config_persistence_error"
    default_message = "Could not persist widget configuration"
