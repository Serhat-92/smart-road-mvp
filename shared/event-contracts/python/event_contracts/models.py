"""Python models for shared event contracts."""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import Field

from .base import ContractModel


def utc_now():
    return datetime.now(timezone.utc)


class BoundingBox(ContractModel):
    x1: float
    y1: float
    x2: float
    y2: float


class FrameMetadata(ContractModel):
    source: str
    frame_index: int = Field(..., ge=0)
    timestamp_ms: float | None = Field(default=None, ge=0)
    source_fps: float | None = Field(default=None, gt=0)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    sampled_fps: float | None = Field(default=None, gt=0)


class Detection(ContractModel):
    label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bounding_box: BoundingBox
    class_id: int | None = None
    track_id: int | None = None


class RadarReading(ContractModel):
    source: str
    reading_id: str
    relative_speed: float
    absolute_speed: float
    patrol_speed: float = 0.0
    patrol_accel: float = 0.0
    signal_confidence: float = Field(..., ge=0.0, le=1.0)
    timestamp_ms: float | None = Field(default=None, ge=0)


class VisualTrack(ContractModel):
    track_id: int | None = None
    label: str | None = None
    speed: float | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    bounding_box: BoundingBox | None = None


class DetectionEvent(ContractModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    event_type: Literal["detection.event"] = "detection.event"
    event_id: UUID = Field(default_factory=uuid4)
    source_service: str
    emitted_at: datetime = Field(default_factory=utc_now)
    frame: FrameMetadata
    detections: list[Detection] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FusedVehicleEvent(ContractModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    event_type: Literal["fused.vehicle_event"] = "fused.vehicle_event"
    event_id: UUID = Field(default_factory=uuid4)
    source_service: str
    emitted_at: datetime = Field(default_factory=utc_now)
    matched: bool
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    fusion_status: str
    track_id: int | None = None
    label: str | None = None
    radar: RadarReading
    visual: VisualTrack | None = None
    fused_speed: float | None = None
    speed_delta: float | None = None
    speed_limit: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SpeedViolationAlert(ContractModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    event_type: Literal["speed.violation_alert"] = "speed.violation_alert"
    event_id: UUID = Field(default_factory=uuid4)
    source_service: str
    emitted_at: datetime = Field(default_factory=utc_now)
    timestamp: datetime = Field(default_factory=utc_now)
    camera_id: str
    severity: Literal["warning", "critical"]
    matched: bool
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    speed_limit: float = Field(..., ge=0.0)
    estimated_speed: float = Field(..., ge=0.0)
    radar_speed: float | None = Field(default=None, ge=0.0)
    fused_speed: float = Field(..., ge=0.0)
    violation_amount: float = Field(..., ge=0.0)
    track_id: int | None = None
    label: str | None = None
    plate_number: str | None = None
    radar: RadarReading | None = None
    visual: VisualTrack | None = None
    image_evidence_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
