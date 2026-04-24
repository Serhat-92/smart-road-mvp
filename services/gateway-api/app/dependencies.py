"""Dependency providers for FastAPI routes."""

from __future__ import annotations

from typing import Literal

from fastapi import Request

from app.container import ServiceContainer
from app.db.session import DatabaseManager
from app.services.device_service import DeviceService
from app.services.event_service import EventService
from app.services.ingest_service import IngestService


def get_container(request: Request) -> ServiceContainer:
    return request.app.state.container


def get_device_service(request: Request) -> DeviceService:
    return get_container(request).device_service


def get_event_service(request: Request) -> EventService:
    return get_container(request).event_service


def get_ingest_service(request: Request) -> IngestService:
    return get_container(request).ingest_service


def get_db_manager(request: Request) -> DatabaseManager:
    """Return the database manager from the application container."""
    return get_container(request).database


def get_repository_mode(request: Request) -> Literal["postgres", "memory"]:
    """Determine which repository path to use based on database connection state."""
    db = get_db_manager(request)
    if db.connected and db.storage_backend == "postgres":
        return "postgres"
    return "memory"


async def get_db_session(request: Request):
    """Yield an AsyncSession when PostgreSQL is connected, otherwise yield None."""
    db = get_db_manager(request)
    if db.connected and db._session_factory is not None:
        async with db._session_factory() as session:
            yield session
    else:
        yield None
