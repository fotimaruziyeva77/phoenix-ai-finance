"""Non-domain configuration errors (mapped to HTTP by ``exception_handlers``)."""


class DatabaseNotConfiguredError(Exception):
    """``DATABASE_URL`` / ``APP_DATABASE_URL`` is missing."""

    def __init__(self) -> None:
        super().__init__(
            "Database is not configured. Set DATABASE_URL (or APP_DATABASE_URL).",
        )
