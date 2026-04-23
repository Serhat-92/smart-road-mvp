"""Simple public API for the AI inference service."""

from .detector import VehicleDetector
from .pipelines import FrameDetectionPipeline, VehicleInferencePipeline, VideoDetectionPipeline
from .radar_fusion import RadarEventFusion, RadarFusionEngine
from .tracker import ApproximateSpeedEstimator, SpeedEstimator
from .utils import (
    FrameDetectionResult,
    FusedViolationEvent,
    InferenceResult,
    RadarSpeedReading,
    VideoDetectionResult,
)


class AIInferenceService:
    """High-level inference facade for single-frame processing."""

    def __init__(
        self,
        detector=None,
        tracker=None,
        fusion_engine=None,
        model_path="yolov8n.pt",
        speed_factor=36.0,
    ):
        self.detector = detector or VehicleDetector(model_path=model_path)
        self.tracker = tracker or SpeedEstimator(speed_factor=speed_factor)
        self.fusion_engine = fusion_engine or RadarFusionEngine()
        self.radar_event_fusion = RadarEventFusion()
        self.pipeline = VehicleInferencePipeline(
            detector=self.detector,
            tracker=self.tracker,
            fusion_engine=self.fusion_engine,
        )
        self.frame_pipeline = FrameDetectionPipeline(detector=self.detector)
        self.video_pipeline = VideoDetectionPipeline(
            detector=self.detector,
            speed_estimator_factory=lambda: ApproximateSpeedEstimator(
                calibration_factor=speed_factor
            ),
        )

    def infer_frame(
        self,
        frame,
        radar_relative_speed=None,
        patrol_speed=0.0,
        patrol_accel=0.0,
    ) -> InferenceResult:
        return self.pipeline.infer(
            frame=frame,
            radar_relative_speed=radar_relative_speed,
            patrol_speed=patrol_speed,
            patrol_accel=patrol_accel,
        )

    def mark_captured(self, track_id: int) -> None:
        self.pipeline.mark_captured(track_id)

    def analyze_frame(
        self,
        frame,
        *,
        source="image-frame",
        frame_index=0,
        timestamp_ms=None,
        source_fps=None,
        sampled_fps=None,
        captured_at=None,
        use_tracking=False,
    ) -> FrameDetectionResult:
        return self.frame_pipeline.run(
            frame=frame,
            source=source,
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            source_fps=source_fps,
            sampled_fps=sampled_fps,
            captured_at=captured_at,
            use_tracking=use_tracking,
        )

    def analyze_image_bytes(
        self,
        image_bytes,
        *,
        source="image-frame",
        frame_index=0,
        timestamp_ms=None,
        source_fps=None,
        sampled_fps=None,
        captured_at=None,
        use_tracking=False,
    ) -> FrameDetectionResult:
        frame = self.decode_image_bytes(image_bytes)
        return self.analyze_frame(
            frame,
            source=source,
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            source_fps=source_fps,
            sampled_fps=sampled_fps,
            captured_at=captured_at,
            use_tracking=use_tracking,
        )

    def infer_video(
        self,
        source,
        sample_rate_fps=1.0,
        max_frames=None,
        use_tracking=False,
        speed_limit=None,
        camera_id=None,
        emit_speed_events=True,
        radar_speed=None,
        event_emitter=None,
        save_evidence=True,
    ) -> VideoDetectionResult:
        return self.video_pipeline.run(
            source=source,
            sample_rate_fps=sample_rate_fps,
            max_frames=max_frames,
            use_tracking=use_tracking,
            speed_limit=speed_limit,
            camera_id=camera_id,
            emit_speed_events=emit_speed_events,
            radar_speed=radar_speed,
            event_emitter=event_emitter,
            save_evidence=save_evidence,
        )

    def fuse_radar_event(
        self,
        vehicle_tracks,
        speed_limit,
        radar_speed_data=None,
        patrol_speed=0.0,
        patrol_accel=0.0,
    ) -> FusedViolationEvent:
        reading = (
            radar_speed_data
            if isinstance(radar_speed_data, RadarSpeedReading)
            else RadarSpeedReading(**radar_speed_data)
            if radar_speed_data is not None
            else None
        )
        return self.radar_event_fusion.fuse_speed_violation_event(
            radar_reading=reading,
            vehicle_tracks=vehicle_tracks,
            speed_limit=speed_limit,
            patrol_speed=patrol_speed,
            patrol_accel=patrol_accel,
        )

    @staticmethod
    def decode_image_bytes(image_bytes):
        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover - optional Docker dependency
            raise RuntimeError("NumPy is required to decode image frames") from exc

        buffer = np.frombuffer(image_bytes, dtype=np.uint8)
        if buffer.size == 0:
            raise ValueError("image_bytes is empty")

        try:
            import cv2
        except ImportError as exc:  # pragma: no cover - runtime dependency
            raise RuntimeError("OpenCV is required to decode image frames") from exc

        frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Unable to decode image bytes into a frame")
        return frame
