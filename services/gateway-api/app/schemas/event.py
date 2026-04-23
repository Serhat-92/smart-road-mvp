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


class EventListResponse(StrictBaseModel):
    items: list[EventRead]
    total: int
