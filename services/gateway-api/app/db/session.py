"""Database session manager with PostgreSQL async support and in-memory fallback."""

from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from app.core.config import Settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


logger = get_logger("gateway_api.database")


class DatabaseManager:
    """Tracks PostgreSQL reachability while allowing in-memory fallback today."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.connected = False
        self.last_error: str | None = None
        self.state = "disabled" if not settings.postgres_enabled else "configured"
        self.storage_backend = "memory"
        self._engine = None
        self._session_factory = None

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
            # TCP probe succeeded — create async engine and session factory
            try:
                from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

                self._engine = create_async_engine(
                    self.settings.postgres_dsn,
                    echo=self.settings.postgres_echo,
                    pool_pre_ping=True,
                )
                self._session_factory = async_sessionmaker(
                    bind=self._engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                )

                # Auto-create tables from ORM models if they don't exist
                from app.db.models import Base

                async with self._engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                logger.info("ORM tables ensured (create_all)")

                self.connected = True
                self.last_error = None
                self.state = "connected"
                self.storage_backend = "postgres"
                logger.info(
                    "PostgreSQL async engine created successfully",
                    extra={
                        "postgres_host": self.settings.postgres_host,
                        "postgres_port": self.settings.postgres_port,
                    },
                )
            except Exception as exc:  # pragma: no cover
                self.connected = False
                self.last_error = f"{type(exc).__name__}: {exc}"
                self.state = "fallback"
                logger.warning(
                    "Failed to create async engine, falling back to in-memory",
                    extra={"error": str(exc)},
                )

    async def disconnect(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
        if self.connected:
            self.connected = False
            self.state = "disconnected"

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Yield an async database session. Only available when connected to PostgreSQL."""
        if self._session_factory is None:
            raise RuntimeError("Database session factory is not available (PostgreSQL not connected)")
        async with self._session_factory() as session:
            yield session

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
