"""Device schemas."""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import Field

from app.core.pydantic import StrictBaseModel


class DeviceCreate(StrictBaseModel):
    device_id: str = Field(..., min_length=1, max_length=100)
    name: str | None = Field(default=None, max_length=200)
    kind: str = Field(default="camera", max_length=100)
    status: Literal["active", "inactive", "maintenance"] = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeviceRead(DeviceCreate):
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DeviceListResponse(StrictBaseModel):
    items: list[DeviceRead]
    total: int
