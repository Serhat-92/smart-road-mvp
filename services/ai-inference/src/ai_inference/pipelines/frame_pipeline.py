"""Single-frame detection pipeline for image or extracted video frames."""

from __future__ import annotations

import math

from ..utils import FrameDetectionResult, FrameMetadata


class FrameDetectionPipeline:
    """Run vehicle detection on a single frame and return structured metadata."""

    def __init__(self, detector):
        self.detector = detector

    def run(
        self,
        frame,
        *,
        source: str = "image-frame",
        frame_index: int = 0,
        timestamp_ms: float | None = None,
        source_fps: float | None = None,
        sampled_fps: float | None = None,
        captured_at: str | None = None,
        use_tracking: bool = False,
    ) -> FrameDetectionResult:
        if frame is None:
            raise ValueError("frame must not be None")

        raw_result = (
            self.detector.detect_and_track(frame)
            if use_tracking
            else self.detector.detect(frame)
        )
        detections = self.detector.to_structured_detections(raw_result)
        height, width = frame.shape[:2]

        normalized_timestamp_ms = None
        if timestamp_ms is not None and math.isfinite(float(timestamp_ms)):
            normalized_timestamp_ms = float(timestamp_ms)

        return FrameDetectionResult(
            frame=FrameMetadata.from_dimensions(
                source=str(source),
                frame_index=int(frame_index),
                width=int(width),
                height=int(height),
                captured_at=captured_at,
                timestamp_ms=normalized_timestamp_ms,
                source_fps=source_fps,
                sampled_fps=sampled_fps,
            ),
            detections=detections,
        )
