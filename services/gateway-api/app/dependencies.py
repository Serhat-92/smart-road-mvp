"""Dependency providers for FastAPI routes."""

from fastapi import Request

from app.container import ServiceContainer
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
