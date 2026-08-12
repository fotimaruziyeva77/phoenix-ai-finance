"""Errors for unauthenticated public widget bootstrap (minimal disclosure)."""

from __future__ import annotations

from typing import ClassVar


class WidgetBootstrapError(Exception):
    status_code: ClassVar[int] = 404
    code: ClassVar[str] = "widget_bootstrap_error"
    default_message: ClassVar[str] = "Widget unavailable."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class WidgetBootstrapNotFoundError(WidgetBootstrapError):
    status_code = 404
    code = "widget_not_found"
    default_message = "Widget not found."


class WidgetBootstrapDisabledError(WidgetBootstrapError):
    status_code = 403
    code = "widget_disabled"
    default_message = "This widget is disabled."


class WidgetBootstrapOriginForbiddenError(WidgetBootstrapError):
    """Embedding denied (wrong origin, missing Origin/Referer when required, or empty allowlist in strict mode)."""

    status_code = 403
    code = "widget_origin_forbidden"
    default_message = "This widget cannot be loaded from this site."


class WidgetBootstrapRuntimeBlockedError(WidgetBootstrapError):
    """Owner inactive, missing, or bot platform-suspended — embed must not load."""

    status_code = 403
    code = "widget_runtime_blocked"
    default_message = "This widget is not available."
