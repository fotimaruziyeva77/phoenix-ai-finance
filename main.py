"""ASGI entrypoint for local and process managers (e.g. uvicorn main:app)."""

import uvicorn

from app.core.config import get_settings
from app.main import app

__all__ = ["app", "main"]


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        factory=False,
        timeout_keep_alive=15,
        limit_concurrency=200,
        limit_max_requests=10_000,
    )


if __name__ == "__main__":
    main()
