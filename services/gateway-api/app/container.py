"""Application container wiring repositories, services, and database state."""

from dataclasses import dataclass

from app.core.config import Settings
from app.core.event_contracts import EventContractValidator
from app.core.logging import get_logger
from app.db.session import DatabaseManager
from app.repositories.device_repository import DeviceRepository
from app.repositories.event_repository import EventRepository
from app.repositories.ingest_repository import FrameIngestRepository
from app.services.device_service import DeviceService
from app.services.event_service import EventService
from app.services.ingest_service import IngestService


logger = get_logger("gateway_api.container")


@dataclass
class ServiceContainer:
    settings: Settings
    database: DatabaseManager
    device_service: DeviceService
    event_service: EventService
    ingest_service: IngestService


def build_container(settings: Settings) -> ServiceContainer:
    database = DatabaseManager(settings=settings)

    device_repository = DeviceRepository()
    event_repository = EventRepository()
    ingest_repository = FrameIngestRepository()
    event_contract_validator = EventContractValidator()

    device_service = DeviceService(repository=device_repository)
    event_service = EventService(
        repository=event_repository,
        contract_validator=event_contract_validator,
    )
    ingest_service = IngestService(
        repository=ingest_repository,
        device_repository=device_repository,
    )

    logger.info(
        "Service container initialized",
        extra={
            "postgres_enabled": settings.postgres_enabled,
            "storage_backend": database.storage_backend,
        },
    )

    return ServiceContainer(
        settings=settings,
        database=database,
        device_service=device_service,
        event_service=event_service,
        ingest_service=ingest_service,
    )
