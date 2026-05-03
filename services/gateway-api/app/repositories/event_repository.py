"""Event persistence adapter with async PostgreSQL support and in-memory fallback."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class EventRepository:
    def __init__(self):
        self._items = []
        self._lock = RLock()

    # ── In-memory (synchronous) fallback methods ───────────────────────

    def list(self):
        with self._lock:
            return deepcopy(self._items)

    def add(self, record: dict):
        with self._lock:
            stored_record = deepcopy(record)
            if "operator_status" not in stored_record:
                stored_record["operator_status"] = "pending"
            self._items.insert(0, stored_record)
            return deepcopy(stored_record)

    def update_status(self, event_id: str, status: str) -> dict | None:
        """Update the operator_status of an in-memory event by id."""
        with self._lock:
            for item in self._items:
                item_id = str(item.get("id", ""))
                if item_id == str(event_id):
                    item["operator_status"] = status
                    return deepcopy(item)
            return None

    # ── PostgreSQL async methods ───────────────────────────────────────

    async def list_async(self, session: AsyncSession) -> list[dict]:
        """List all events from PostgreSQL, newest first."""
        from sqlalchemy import select

        from app.db.models import EventRecord

        stmt = select(EventRecord).order_by(EventRecord.created_at.desc())
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [self._orm_to_dict(row) for row in rows]

    async def add_async(self, session: AsyncSession, record: dict) -> dict:
        """Insert an event into PostgreSQL and return the stored record dict."""
        from app.db.models import EventRecord

        payload = record.get("payload", {})
        orm_record = EventRecord(
            id=record.get("id", uuid4()),
            event_type=record.get("event_type", ""),
            camera_id=payload.get("camera_id") or record.get("device_id") or "unknown",
            severity=record.get("severity", "info"),
            estimated_speed=payload.get("estimated_speed"),
            speed_limit=payload.get("speed_limit"),
            fused_speed=payload.get("fused_speed"),
            violation_amount=payload.get("violation_amount"),
            track_id=payload.get("track_id"),
            label=payload.get("label"),
            image_evidence_path=payload.get("image_evidence_path"),
            plate_number=payload.get("plate_number"),
            payload=payload,
            operator_status=record.get("operator_status", "pending"),
            created_at=record.get("created_at", datetime.now(timezone.utc)),
        )
        session.add(orm_record)
        await session.commit()
        await session.refresh(orm_record)
        return self._orm_to_dict(orm_record)

    async def update_status_async(
        self, session: AsyncSession, event_id: str, status: str
    ) -> dict | None:
        """Update the operator_status of an event in PostgreSQL."""
        from sqlalchemy import select

        from app.db.models import EventRecord

        stmt = select(EventRecord).where(EventRecord.id == event_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.operator_status = status
        await session.commit()
        await session.refresh(row)
        return self._orm_to_dict(row)

    @staticmethod
    def _orm_to_dict(row) -> dict:
        """Convert an EventRecord ORM instance to a plain dict matching EventRead schema."""
        image_evidence_path = row.image_evidence_path
        evidence_url = None
        if image_evidence_path:
            normalized_path = str(image_evidence_path).replace("\\", "/").lstrip("/")
            for prefix in ("datasets/evidence/", "app/datasets/evidence/"):
                if normalized_path.startswith(prefix):
                    normalized_path = normalized_path[len(prefix):]
                    break
            evidence_url = f"/evidence/{normalized_path}"

        return {
            "id": row.id,
            "event_type": row.event_type,
            "device_id": row.camera_id,
            "severity": row.severity,
            "payload": row.payload or {},
            "occurred_at": row.created_at,
            "created_at": row.created_at,
            "plate_number": row.plate_number,
            "image_evidence_path": image_evidence_path,
            "evidence_url": evidence_url,
            "operator_status": row.operator_status,
        }
