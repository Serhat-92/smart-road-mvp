"""Frame-by-frame inference pipeline."""

from ..radar_fusion import RadarFusionEngine
from ..utils import FusionMetadata, InferenceResult


class VehicleInferencePipeline:
    def __init__(self, detector, tracker, fusion_engine=None):
        self.detector = detector
        self.tracker = tracker
        self.fusion_engine = fusion_engine or RadarFusionEngine()

    def infer(
        self,
        frame,
        radar_relative_speed=None,
        patrol_speed=0.0,
        patrol_accel=0.0,
    ) -> InferenceResult:
        detections = self.detector.detect_and_track(frame)
        vehicle_data = self.tracker.update(detections)
        fusion = FusionMetadata(
            radar_relative_speed=radar_relative_speed,
            patrol_speed=patrol_speed,
            patrol_accel=patrol_accel,
        )

        if radar_relative_speed is not None:
            vehicle_data, fusion = self.fusion_engine.apply(
                vehicle_data=vehicle_data,
                radar_relative_speed=radar_relative_speed,
                patrol_speed=patrol_speed,
                patrol_accel=patrol_accel,
            )

        return InferenceResult(
            raw_detections=detections,
            vehicle_data=vehicle_data,
            fusion=fusion,
        )

    def mark_captured(self, track_id: int) -> None:
        self.tracker.mark_captured(track_id)
