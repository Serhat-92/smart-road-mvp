"""Common datatypes for inference modules."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class FusionMetadata:
    radar_relative_speed: float | None = None
    radar_absolute_speed: float = 0.0
    patrol_speed: float = 0.0
    patrol_accel: float = 0.0
    is_stable: bool = True
    matched_track_id: int | None = None
    match_difference: float | None = None


@dataclass
class InferenceResult:
    raw_detections: Any
    vehicle_data: dict[int, dict[str, Any]] = field(default_factory=dict)
    fusion: FusionMetadata = field(default_factory=FusionMetadata)

    @property
    def track_count(self) -> int:
        return len(self.vehicle_data)

    def speeding_tracks(self, max_speed: float) -> dict[int, dict[str, Any]]:
        return {
            track_id: data
            for track_id, data in self.vehicle_data.items()
            if data.get("speed", 0.0) > max_speed
        }


@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass
class SpeedEstimate:
    relative_speed_kmh: float | None = None
    source: str = "computer_vision_approx"
    method: str = "normalized_pixel_displacement"
    is_approximate: bool = True
    calibration_factor: float | None = None
    correction_status: str = "uncorrected"
    corrected_speed_kmh: float | None = None


@dataclass
class DetectionRecord:
    label: str
    confidence: float
    bounding_box: BoundingBox
    class_id: int | None = None
    track_id: int | None = None
    speed_estimate: SpeedEstimate | None = None


@dataclass
class FrameMetadata:
    source: str
    frame_index: int
    captured_at: str | None = None
    timestamp_ms: float | None = None
    source_fps: float | None = None
    width: int | None = None
    height: int | None = None
    sampled_fps: float | None = None

    @classmethod
    def from_dimensions(
        cls,
        *,
        source: str,
        frame_index: int,
        width: int,
        height: int,
        captured_at: str | None = None,
        timestamp_ms: float | None = None,
        source_fps: float | None = None,
        sampled_fps: float | None = None,
    ) -> "FrameMetadata":
        return cls(
            source=source,
            frame_index=frame_index,
            captured_at=captured_at or datetime.now(timezone.utc).isoformat(),
            timestamp_ms=timestamp_ms,
            source_fps=source_fps,
            width=width,
            height=height,
            sampled_fps=sampled_fps,
        )


@dataclass
class FrameDetectionResult:
    frame: FrameMetadata
    detections: list[DetectionRecord] = field(default_factory=list)


@dataclass
class VideoDetectionResult:
    source: str
    sample_rate_fps: float
    processed_frames: int
    sampled_frames: int
    source_fps: float | None = None
    frames: list[FrameDetectionResult] = field(default_factory=list)
    generated_events: list["GeneratedEventRecord"] = field(default_factory=list)

    @property
    def total_detections(self) -> int:
        return sum(len(frame_result.detections) for frame_result in self.frames)

    @property
    def generated_event_count(self) -> int:
        return len(self.generated_events)


@dataclass
class RadarSpeedReading:
    relative_speed: float
    patrol_speed: float = 0.0
    patrol_accel: float = 0.0
    source: str = "simulated-radar"
    signal_confidence: float = 1.0
    reading_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp_ms: float | None = None

    @property
    def absolute_speed(self) -> float:
        return self.relative_speed + self.patrol_speed


@dataclass
class RadarTrackMatch:
    matched: bool
    track_id: int | None
    confidence_score: float
    radar_speed: float
    visual_speed: float | None = None
    speed_delta: float | None = None
    label: str | None = None
    bounding_box: BoundingBox | None = None
    detection_confidence: float | None = None
    fusion_status: str = "UNMATCHED"


@dataclass
class FusedViolationEvent:
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = "speed_observation"
    source: str = "simulated-radar"
    matched: bool = False
    is_potential_violation: bool = False
    confidence_score: float = 0.0
    speed_limit: float = 0.0
    fused_speed: float | None = None
    estimated_speed: float | None = None
    violation_amount: float | None = None
    radar_speed: float = 0.0
    radar_relative_speed: float = 0.0
    visual_speed: float | None = None
    speed_delta: float | None = None
    track_id: int | None = None
    label: str | None = None
    bounding_box: BoundingBox | None = None
    fusion_status: str = "UNMATCHED"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        bbox = None
        if self.bounding_box is not None:
            bbox = {
                "x1": self.bounding_box.x1,
                "y1": self.bounding_box.y1,
                "x2": self.bounding_box.x2,
                "y2": self.bounding_box.y2,
            }

        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "matched": self.matched,
            "is_potential_violation": self.is_potential_violation,
            "confidence_score": self.confidence_score,
            "speed_limit": self.speed_limit,
            "road_speed_limit": self.speed_limit,
            "fused_speed": self.fused_speed,
            "estimated_speed": self.estimated_speed,
            "violation_amount": self.violation_amount,
            "radar_speed": self.radar_speed,
            "radar_relative_speed": self.radar_relative_speed,
            "visual_speed": self.visual_speed,
            "speed_delta": self.speed_delta,
            "track_id": self.track_id,
            "label": self.label,
            "bounding_box": bbox,
            "fusion_status": self.fusion_status,
            "metadata": self.metadata,
        }


@dataclass
class GeneratedEventRecord:
    event_type: str
    camera_id: str
    timestamp: str
    track_id: int | None = None
    estimated_speed: float | None = None
    radar_speed: float | None = None
    confidence_score: float = 0.0
    image_evidence_path: str | None = None
    delivery_status: str = "pending"
    gateway_event_id: str | None = None
    gateway_status_code: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)
