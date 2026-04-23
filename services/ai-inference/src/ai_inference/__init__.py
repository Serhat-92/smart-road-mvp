"""AI inference service package."""

from .api import AIInferenceService
from .detector import VehicleDetector
from .eventing import EvidenceStore, GatewayEventPublisher, SpeedViolationEventEmitter
from .pipelines import (
    FrameDetectionPipeline,
    LocalVideoFileSource,
    RTSPVideoSource,
    VehicleInferencePipeline,
    VideoDetectionPipeline,
    VideoSourceFactory,
)
from .radar_fusion import RadarEventFusion, RadarFusionEngine, RadarSpeedSimulator
from .tracker import ApproximateSpeedEstimator, SimpleMultiObjectTracker, SpeedEstimator
from .utils import (
    BoundingBox,
    DetectionRecord,
    FusedViolationEvent,
    FrameDetectionResult,
    FrameMetadata,
    FusionMetadata,
    GeneratedEventRecord,
    InferenceResult,
    RadarSpeedReading,
    RadarTrackMatch,
    SpeedEstimate,
    VideoDetectionResult,
)


def main(*args, **kwargs):
    from .main import main as _main

    return _main(*args, **kwargs)


def main_cli(*args, **kwargs):
    from .main import main_cli as _main_cli

    return _main_cli(*args, **kwargs)


__all__ = [
    "AIInferenceService",
    "BoundingBox",
    "DetectionRecord",
    "EvidenceStore",
    "FrameDetectionPipeline",
    "LocalVideoFileSource",
    "RTSPVideoSource",
    "FusedViolationEvent",
    "FrameDetectionResult",
    "FrameMetadata",
    "FusionMetadata",
    "GeneratedEventRecord",
    "GatewayEventPublisher",
    "InferenceResult",
    "RadarEventFusion",
    "RadarFusionEngine",
    "RadarSpeedSimulator",
    "RadarSpeedReading",
    "RadarTrackMatch",
    "ApproximateSpeedEstimator",
    "SpeedViolationEventEmitter",
    "SpeedEstimate",
    "SimpleMultiObjectTracker",
    "SpeedEstimator",
    "VehicleDetector",
    "VideoDetectionPipeline",
    "VideoDetectionResult",
    "VehicleInferencePipeline",
    "main",
    "main_cli",
    "VideoSourceFactory",
]
