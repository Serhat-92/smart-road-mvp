"""Event schemas."""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import Field

from app.core.pydantic import StrictBaseModel


class EventCreate(StrictBaseModel):
    event_type: str = Field(..., min_length=1, max_length=100)
    device_id: str | None = Field(default=None, max_length=100)
    severity: Literal["info", "warning", "critical"] = "info"
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EventRead(StrictBaseModel):
    id: UUID = Field(default_factory=uuid4)
    event_type: str
    device_id: str | None = None
    severity: str
    payload: dict[str, Any]
    occurred_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    plate_number: str | None = None
    operator_status: str = "pending"


class EventStatusUpdate(StrictBaseModel):
    status: Literal["pending", "reviewed", "dismissed"]


class EventListResponse(StrictBaseModel):
    items: list[EventRead]
    total: int


class CameraStats(StrictBaseModel):
    camera_id: str
    count: int


class EventStats(StrictBaseModel):
    total_events: int
    pending_count: int
    reviewed_count: int
    dismissed_count: int
    critical_count: int
    warning_count: int
    info_count: int
    avg_radar_speed: float | None
    avg_estimated_speed: float | None
    top_cameras: list[CameraStats]
    events_last_hour: int
