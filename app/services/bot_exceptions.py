"""Domain errors for bot management flows."""

from __future__ import annotations

from typing import ClassVar


class BotServiceError(Exception):
    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "bot_error"
    default_message: ClassVar[str] = "Bot operation failed"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class BotValidationError(BotServiceError):
    status_code = 422
    code = "bot_validation_error"
    default_message = "Bot payload is invalid"


class BotNotFoundError(BotServiceError):
    status_code = 404
    code = "bot_not_found"
    default_message = "Bot was not found"


class BotForbiddenError(BotServiceError):
    status_code = 403
    code = "bot_forbidden"
    default_message = "You do not have access to this bot"


class BotPersistenceError(BotServiceError):
    status_code = 500
    code = "bot_persistence_error"
    default_message = "Could not persist bot changes"


class BotDatabaseUnavailableError(BotServiceError):
    """Transient DB connectivity / pool issues (maps to HTTP 503)."""

    status_code = 503
    code = "database_unavailable"
    default_message = "Database is temporarily unavailable; retry shortly"


class BotReadSerializationError(BotServiceError):
    """ORM row could not be mapped to :class:`~app.schemas.bots.BotRead` (unexpected schema drift)."""

    status_code = 500
    code = "bot_read_serialization_failed"
    default_message = "Bot was created but the response could not be built; check server logs"
