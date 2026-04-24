"""Device persistence adapter with async PostgreSQL support and in-memory fallback."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class DeviceRepository:
    def __init__(self):
        self._items = {}
        self._lock = RLock()

    # ── In-memory (synchronous) fallback methods ───────────────────────

    def list(self):
        with self._lock:
            return deepcopy(list(self._items.values()))

    def get(self, device_id: str):
        with self._lock:
            record = self._items.get(device_id)
            return deepcopy(record) if record is not None else None

    def upsert(self, record: dict):
        with self._lock:
            stored_record = deepcopy(record)
            self._items[record["device_id"]] = stored_record
            return deepcopy(stored_record)

    # ── PostgreSQL async methods ───────────────────────────────────────

    async def list_async(self, session: AsyncSession) -> list[dict]:
        """List all devices from PostgreSQL."""
        from sqlalchemy import select

        from app.db.models import DeviceRecord

        stmt = select(DeviceRecord).order_by(DeviceRecord.updated_at.desc())
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [self._orm_to_dict(row) for row in rows]

    async def get_async(self, session: AsyncSession, device_id: str) -> dict | None:
        """Get a device by ID from PostgreSQL."""
        from sqlalchemy import select

        from app.db.models import DeviceRecord

        stmt = select(DeviceRecord).where(DeviceRecord.device_id == device_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._orm_to_dict(row) if row is not None else None

    async def upsert_async(self, session: AsyncSession, record: dict) -> dict:
        """Insert or update a device in PostgreSQL."""
        from sqlalchemy import select

        from app.db.models import DeviceRecord

        device_id = record["device_id"]
        stmt = select(DeviceRecord).where(DeviceRecord.device_id == device_id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.name = record.get("name", existing.name)
            existing.status = record.get("status", existing.status)
            existing.payload = record.get("metadata", existing.payload)
            existing.updated_at = datetime.now(timezone.utc)
        else:
            existing = DeviceRecord(
                device_id=device_id,
                name=record.get("name"),
                status=record.get("status", "active"),
                payload=record.get("metadata", {}),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(existing)

        await session.commit()
        await session.refresh(existing)
        return self._orm_to_dict(existing)

    @staticmethod
    def _orm_to_dict(row) -> dict:
        """Convert a DeviceRecord ORM instance to a dict matching DeviceRead schema."""
        payload = row.payload or {}
        return {
            "device_id": row.device_id,
            "name": row.name,
            "kind": payload.get("kind", "camera"),
            "status": row.status,
            "metadata": payload,
            "registered_at": payload.get("registered_at", row.updated_at),
            "updated_at": row.updated_at,
        }
