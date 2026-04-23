"""Event application service."""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import ValidationError

from app.core.errors import EventPayloadValidationError
from app.core.logging import get_logger
from app.core.pydantic import model_to_dict
from app.core.event_contracts import EventContractValidator
from app.repositories.event_repository import EventRepository
from app.schemas.event import EventCreate, EventRead


logger = get_logger("gateway_api.events")


class EventService:
    def __init__(
        self,
        repository: EventRepository,
        contract_validator: EventContractValidator | None = None,
    ):
        self.repository = repository
        self.contract_validator = contract_validator or EventContractValidator()

    def list_events(self) -> list[EventRead]:
        return [EventRead(**record) for record in self.repository.list()]

    def create_event(self, payload: EventCreate) -> EventRead:
        now = datetime.now(timezone.utc)
        payload_dict = model_to_dict(payload)
        payload_dict["event_type"] = payload.event_type.strip()
        payload_dict["device_id"] = payload.device_id.strip() if payload.device_id else None

        try:
            payload_dict["payload"] = self.contract_validator.validate(
                event_type=payload_dict["event_type"],
                payload=payload.payload,
            )
        except ValidationError as exc:
            raise EventPayloadValidationError(details=exc.errors()) from exc

        record = {
            "id": uuid4(),
            **payload_dict,
            "created_at": now,
        }
        saved = self.repository.add(record)
        logger.info(
            "Event stored",
            extra={
                "event_type": saved["event_type"],
                "device_id": saved["device_id"],
                "severity": saved["severity"],
            },
        )
        return EventRead(**saved)
