"""Frame ingest schemas."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from app.core.pydantic import StrictBaseModel


class FrameIngestRequest(StrictBaseModel):
    device_id: str = Field(..., min_length=1, max_length=100)
    frame_id: str | None = Field(default=None, max_length=120)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    media_url: str | None = Field(default=None, max_length=500)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FrameIngestResponse(StrictBaseModel):
    ingest_id: UUID = Field(default_factory=uuid4)
    device_id: str
    frame_id: str | None = None
    accepted: bool = True
    queue_status: str = "queued"
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    known_device: bool
