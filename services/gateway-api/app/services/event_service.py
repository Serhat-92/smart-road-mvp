"""Event application service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import ValidationError

from app.core.errors import EventPayloadValidationError
from app.core.logging import get_logger
from app.core.pydantic import model_to_dict
from app.core.event_contracts import EventContractValidator
from app.repositories.event_repository import EventRepository
from app.schemas.event import EventCreate, EventRead

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


logger = get_logger("gateway_api.events")


class EventService:
    def __init__(
        self,
        repository: EventRepository,
        contract_validator: EventContractValidator | None = None,
    ):
        self.repository = repository
        self.contract_validator = contract_validator or EventContractValidator()

    # ── In-memory (synchronous) fallback methods ───────────────────────

    def list_events(self) -> list[EventRead]:
        return [EventRead(**record) for record in self.repository.list()]

    def create_event(self, payload: EventCreate) -> EventRead:
        record = self._prepare_record(payload)
        saved = self.repository.add(record)
        self._log_stored(saved)
        return EventRead(**saved)

    # ── PostgreSQL async methods ───────────────────────────────────────

    async def list_events_async(self, session: AsyncSession) -> list[EventRead]:
        try:
            rows = await self.repository.list_async(session)
            return [EventRead(**record) for record in rows]
        except Exception as exc:
            logger.warning(
                "PostgreSQL list_async failed, falling back to in-memory",
                extra={
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )
            return self.list_events()

    async def create_event_async(
        self, payload: EventCreate, session: AsyncSession
    ) -> EventRead:
        record = self._prepare_record(payload)
        try:
            saved = await self.repository.add_async(session, record)
            self._log_stored(saved)
            return EventRead(**saved)
        except Exception as exc:
            logger.warning(
                "PostgreSQL add_async failed, falling back to in-memory",
                extra={
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )
            # Rollback the failed session
            try:
                await session.rollback()
            except Exception:
                pass
            saved = self.repository.add(record)
            self._log_stored(saved)
            return EventRead(**saved)

    # ── Helpers ────────────────────────────────────────────────────────

    def _prepare_record(self, payload: EventCreate) -> dict:
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

        return {
            "id": uuid4(),
            **payload_dict,
            "created_at": now,
        }

    @staticmethod
    def _log_stored(saved: dict) -> None:
        logger.info(
            "Event stored",
            extra={
                "event_type": saved["event_type"],
                "device_id": saved.get("device_id"),
                "severity": saved["severity"],
            },
        )
