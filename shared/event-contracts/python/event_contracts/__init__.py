"""Shared event contract models."""

from .models import (
    BoundingBox,
    Detection,
    DetectionEvent,
    FrameMetadata,
    FusedVehicleEvent,
    RadarReading,
    SpeedViolationAlert,
    VisualTrack,
)

__all__ = [
    "BoundingBox",
    "Detection",
    "DetectionEvent",
    "FrameMetadata",
    "FusedVehicleEvent",
    "RadarReading",
    "SpeedViolationAlert",
    "VisualTrack",
]
