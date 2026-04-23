"""Convenience runner for the gateway API service."""

import uvicorn

from app.main import app
from app.core.config import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        access_log=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
