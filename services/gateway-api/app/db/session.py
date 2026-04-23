"""Database session manager placeholder for future PostgreSQL integration."""

from __future__ import annotations

import asyncio
import socket

from app.core.config import Settings
from app.core.logging import get_logger


logger = get_logger("gateway_api.database")


class DatabaseManager:
    """Tracks PostgreSQL reachability while allowing in-memory fallback today."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.connected = False
        self.last_error: str | None = None
        self.state = "disabled" if not settings.postgres_enabled else "configured"
        self.storage_backend = "memory"

    async def connect(self) -> None:
        if not self.settings.postgres_enabled:
            self.connected = False
            self.last_error = None
            self.state = "disabled"
            return

        self.state = "connecting"
        try:
            await asyncio.to_thread(self._probe_tcp_connectivity)
        except OSError as exc:
            self.connected = False
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.state = "fallback"
            logger.warning(
                "PostgreSQL unavailable, continuing with in-memory repositories",
                extra={
                    "postgres_host": self.settings.postgres_host,
                    "postgres_port": self.settings.postgres_port,
                    "fallback_backend": self.storage_backend,
                },
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            self.connected = False
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.state = "fallback"
            logger.warning(
                "Unexpected PostgreSQL connectivity failure, using in-memory repositories",
                extra={"fallback_backend": self.storage_backend},
            )
        else:
            self.connected = True
            self.last_error = None
            self.state = "connected"
            logger.info(
                "PostgreSQL connectivity probe succeeded",
                extra={
                    "postgres_host": self.settings.postgres_host,
                    "postgres_port": self.settings.postgres_port,
                },
            )

    async def disconnect(self) -> None:
        if self.connected:
            self.connected = False
            self.state = "disconnected"

    def status_snapshot(self) -> dict:
        return {
            "enabled": self.settings.postgres_enabled,
            "connected": self.connected,
            "state": self.state,
            "dsn": self.settings.redacted_postgres_dsn
            if self.settings.postgres_enabled
            else None,
            "last_error": self.last_error,
        }

    def storage_status_snapshot(self) -> dict:
        fallback_active = self.settings.postgres_enabled and not self.connected
        return {
            "backend": self.storage_backend,
            "fallback_active": fallback_active,
            "reason": self.last_error if fallback_active else None,
        }

    def _probe_tcp_connectivity(self) -> None:
        with socket.create_connection(
            (self.settings.postgres_host, self.settings.postgres_port),
            timeout=self.settings.postgres_connect_timeout_seconds,
        ):
            return
