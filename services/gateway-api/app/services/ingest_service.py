"""Frame ingest application service."""

from datetime import datetime, timezone
from uuid import uuid4

from app.core.errors import IngestValidationError
from app.core.logging import get_logger
from app.core.pydantic import model_to_dict
from app.repositories.device_repository import DeviceRepository
from app.repositories.ingest_repository import FrameIngestRepository
from app.schemas.device import DeviceCreate
from app.schemas.ingest import FrameIngestRequest, FrameIngestResponse


logger = get_logger("gateway_api.ingest")


class IngestService:
    def __init__(
        self,
        repository: FrameIngestRepository,
        device_repository: DeviceRepository,
    ):
        self.repository = repository
        self.device_repository = device_repository

    def ingest_frame(self, payload: FrameIngestRequest) -> FrameIngestResponse:
        if (payload.width is None) != (payload.height is None):
            raise IngestValidationError(
                details=[{"loc": ["body", "width"], "msg": "width and height must be provided together"}]
            )

        normalized_device_id = payload.device_id.strip()
        known_device = self.device_repository.get(normalized_device_id) is not None

        if not known_device:
            # Soft-register unknown devices so ingest can proceed during field rollout.
            now = datetime.now(timezone.utc)
            self.device_repository.upsert(
                {
                    **model_to_dict(DeviceCreate(device_id=normalized_device_id)),
                    "registered_at": now,
                    "updated_at": now,
                }
            )

        response = FrameIngestResponse(
            ingest_id=uuid4(),
            device_id=normalized_device_id,
            frame_id=payload.frame_id.strip() if payload.frame_id else None,
            received_at=datetime.now(timezone.utc),
            known_device=known_device,
        )

        payload_dict = model_to_dict(payload)
        payload_dict["device_id"] = normalized_device_id
        payload_dict["frame_id"] = payload.frame_id.strip() if payload.frame_id else None
        payload_dict["media_url"] = payload.media_url.strip() if payload.media_url else None

        self.repository.add(
            {
                **payload_dict,
                **model_to_dict(response),
            }
        )

        logger.info(
            "Frame ingest accepted",
            extra={
                "device_id": response.device_id,
                "frame_id": response.frame_id,
                "known_device": response.known_device,
                "queue_status": response.queue_status,
            },
        )

        return response
