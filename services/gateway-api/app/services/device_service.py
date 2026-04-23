"""Device application service."""

from datetime import datetime, timezone

from app.core.logging import get_logger
from app.core.pydantic import model_to_dict
from app.repositories.device_repository import DeviceRepository
from app.schemas.device import DeviceCreate, DeviceRead


logger = get_logger("gateway_api.devices")


class DeviceService:
    def __init__(self, repository: DeviceRepository):
        self.repository = repository

    def list_devices(self) -> list[DeviceRead]:
        return [DeviceRead(**record) for record in self.repository.list()]

    def register_device(self, payload: DeviceCreate) -> DeviceRead:
        existing = self.repository.get(payload.device_id)
        now = datetime.now(timezone.utc)
        payload_dict = model_to_dict(payload)
        payload_dict["device_id"] = payload.device_id.strip()
        payload_dict["name"] = payload.name.strip() if payload.name else None
        payload_dict["kind"] = payload.kind.strip().lower()

        if existing:
            record = {
                **existing,
                **payload_dict,
                "registered_at": existing["registered_at"],
                "updated_at": now,
            }
        else:
            record = {
                **payload_dict,
                "registered_at": now,
                "updated_at": now,
            }

        saved = self.repository.upsert(record)
        logger.info(
            "Device upserted",
            extra={
                "device_id": saved["device_id"],
                "device_kind": saved["kind"],
                "device_status": saved["status"],
            },
        )
        return DeviceRead(**saved)
