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

    def get_stats(self) -> EventStats:
        items = self.repository.list()
        now = datetime.now(timezone.utc)
        
        total = len(items)
        pending = sum(1 for x in items if x.get("operator_status") == "pending")
        reviewed = sum(1 for x in items if x.get("operator_status") == "reviewed")
        dismissed = sum(1 for x in items if x.get("operator_status") == "dismissed")
        critical = sum(1 for x in items if x.get("severity") == "critical")
        warning = sum(1 for x in items if x.get("severity") == "warning")
        info = sum(1 for x in items if x.get("severity") == "info")
        
        radar_speeds = [x["payload"].get("radar_speed") for x in items if isinstance(x.get("payload"), dict) and x["payload"].get("radar_speed") is not None]
        avg_radar = sum(radar_speeds) / len(radar_speeds) if radar_speeds else None
        
        estimated_speeds = [x.get("estimated_speed") or (x["payload"].get("estimated_speed") if isinstance(x.get("payload"), dict) else None) for x in items]
        estimated_speeds = [s for s in estimated_speeds if s is not None]
        avg_estimated = sum(estimated_speeds) / len(estimated_speeds) if estimated_speeds else None
        
        last_hour = sum(1 for x in items if (now - x.get("created_at", now)).total_seconds() <= 3600)
        
        from collections import Counter
        camera_counts = Counter(x.get("device_id") or "unknown" for x in items)
        top_cameras = [{"camera_id": k, "count": v} for k, v in camera_counts.most_common(3)]
        
        from app.schemas.event import EventStats
        return EventStats(
            total_events=total,
            pending_count=pending,
            reviewed_count=reviewed,
            dismissed_count=dismissed,
            critical_count=critical,
            warning_count=warning,
            info_count=info,
            avg_radar_speed=avg_radar,
            avg_estimated_speed=avg_estimated,
            top_cameras=top_cameras,
            events_last_hour=last_hour
        )

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

    async def get_stats_async(self, session: AsyncSession) -> EventStats:
        try:
            from sqlalchemy import select, func, text, cast, Float, Integer
            from app.db.models import EventRecord
            from app.schemas.event import EventStats
            
            # Simple aggregations using filter instead of cast to support all PG versions cleanly
            stmt = select(
                func.count(EventRecord.id),
                func.count(EventRecord.id).filter(EventRecord.operator_status == 'pending'),
                func.count(EventRecord.id).filter(EventRecord.operator_status == 'reviewed'),
                func.count(EventRecord.id).filter(EventRecord.operator_status == 'dismissed'),
                func.count(EventRecord.id).filter(EventRecord.severity == 'critical'),
                func.count(EventRecord.id).filter(EventRecord.severity == 'warning'),
                func.count(EventRecord.id).filter(EventRecord.severity == 'info'),
                func.count(EventRecord.id).filter(EventRecord.created_at >= func.now() - text("INTERVAL '1 hour'")),
            )
            result = await session.execute(stmt)
            total, pending, reviewed, dismissed, critical, warning, info, last_hour = result.first()
            
            stmt_avg = select(
                func.avg(cast(EventRecord.payload['radar_speed'].astext, Float)),
                func.avg(EventRecord.estimated_speed)
            )
            result_avg = await session.execute(stmt_avg)
            avg_radar, avg_est = result_avg.first()
            
            stmt_top = select(EventRecord.camera_id, func.count(EventRecord.id)).group_by(EventRecord.camera_id).order_by(func.count(EventRecord.id).desc()).limit(3)
            result_top = await session.execute(stmt_top)
            top_cams = [{"camera_id": row[0], "count": row[1]} for row in result_top.all()]
            
            return EventStats(
                total_events=total or 0,
                pending_count=pending or 0,
                reviewed_count=reviewed or 0,
                dismissed_count=dismissed or 0,
                critical_count=critical or 0,
                warning_count=warning or 0,
                info_count=info or 0,
                avg_radar_speed=avg_radar,
                avg_estimated_speed=avg_est,
                top_cameras=top_cams,
                events_last_hour=last_hour or 0
            )
            
        except Exception as exc:
            logger.warning(
                "PostgreSQL get_stats_async failed, falling back to in-memory",
                extra={
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )
            return self.get_stats()

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
