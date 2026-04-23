"""Integration tests for the local-file video detection pipeline."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import cv2
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
AI_INFERENCE_ROOT = REPO_ROOT / "services" / "ai-inference"

ai_inference_root_str = str(AI_INFERENCE_ROOT)
if ai_inference_root_str not in sys.path:
    sys.path.insert(0, ai_inference_root_str)

from src.ai_inference.pipelines import VideoDetectionPipeline
from src.ai_inference.utils import BoundingBox, DetectionRecord, GeneratedEventRecord


class _FakeDetector:
    def __init__(self):
        self._call_count = 0

    def detect(self, frame):
        self._call_count += 1
        return {"shape": frame.shape, "call_count": self._call_count}

    def detect_and_track(self, frame):
        return self.detect(frame)

    def to_structured_detections(self, result):
        height, width = result["shape"][:2]
        shift = float((result["call_count"] - 1) * 12)
        return [
            DetectionRecord(
                label="car",
                confidence=0.95,
                bounding_box=BoundingBox(
                    x1=10.0 + shift,
                    y1=20.0,
                    x2=float(width - 10 + shift),
                    y2=float(height - 20),
                ),
                class_id=2,
                track_id=None,
            )
        ]


class VideoDetectionPipelineTests(unittest.TestCase):
    def create_test_video(self, path: Path, frame_count: int = 6, fps: float = 6.0):
        writer = cv2.VideoWriter(
            str(path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (320, 240),
        )
        for index in range(frame_count):
            frame = np.full((240, 320, 3), fill_value=index * 20, dtype=np.uint8)
            writer.write(frame)
        writer.release()

    def test_local_video_pipeline_samples_frames_and_returns_structured_detections(self):
        pipeline = VideoDetectionPipeline(detector=_FakeDetector())

        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "sample.mp4"
            self.create_test_video(video_path, frame_count=6, fps=6.0)

            result = pipeline.run(
                source=str(video_path),
                sample_rate_fps=2.0,
                max_frames=6,
                use_tracking=False,
            )

        self.assertEqual(result.processed_frames, 6)
        self.assertEqual(result.sampled_frames, 2)
        self.assertEqual(result.total_detections, 2)
        self.assertEqual(result.source_fps, 6.0)
        self.assertEqual(result.frames[0].frame.frame_index, 0)
        self.assertEqual(result.frames[1].frame.frame_index, 3)
        self.assertEqual(result.frames[0].detections[0].label, "car")
        self.assertEqual(result.frames[0].frame.width, 320)
        self.assertEqual(result.frames[0].frame.height, 240)
        self.assertIsNone(result.frames[0].detections[0].track_id)

    def test_rtsp_sources_are_explicitly_rejected_for_now(self):
        pipeline = VideoDetectionPipeline(detector=_FakeDetector())
        with self.assertRaises(NotImplementedError):
            pipeline.run(source="rtsp://camera-01/stream", sample_rate_fps=1.0)

    def test_tracking_keeps_consistent_ids_across_sampled_frames(self):
        pipeline = VideoDetectionPipeline(detector=_FakeDetector())

        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "tracked.mp4"
            self.create_test_video(video_path, frame_count=6, fps=6.0)

            result = pipeline.run(
                source=str(video_path),
                sample_rate_fps=2.0,
                max_frames=6,
                use_tracking=True,
            )

        self.assertEqual(result.sampled_frames, 2)
        first_track_id = result.frames[0].detections[0].track_id
        second_track_id = result.frames[1].detections[0].track_id
        self.assertIsNotNone(first_track_id)
        self.assertEqual(first_track_id, second_track_id)
        self.assertIsNotNone(result.frames[1].detections[0].speed_estimate)
        self.assertTrue(result.frames[1].detections[0].speed_estimate.is_approximate)
        self.assertEqual(
            result.frames[1].detections[0].speed_estimate.source,
            "computer_vision_approx",
        )
        self.assertEqual(
            result.frames[1].detections[0].speed_estimate.correction_status,
            "uncorrected",
        )

    def test_speed_limit_generates_single_event_for_tracked_vehicle(self):
        class _FakeEventEmitter:
            def __init__(self):
                self.calls = []

            def emit_speed_violation(self, **kwargs):
                self.calls.append(kwargs)
                detection = kwargs["detection"]
                return GeneratedEventRecord(
                    event_type="speed.violation_alert",
                    camera_id=kwargs["camera_id"],
                    timestamp="2026-04-22T12:00:00+00:00",
                    track_id=detection.track_id,
                    estimated_speed=detection.speed_estimate.relative_speed_kmh,
                    radar_speed=kwargs["radar_speed"],
                    confidence_score=detection.confidence,
                    image_evidence_path="datasets/evidence/camera-01/evidence.jpg",
                    delivery_status="sent",
                    gateway_event_id="evt-1",
                    gateway_status_code=201,
                )

        pipeline = VideoDetectionPipeline(detector=_FakeDetector())
        event_emitter = _FakeEventEmitter()

        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "violations.mp4"
            self.create_test_video(video_path, frame_count=6, fps=6.0)

            result = pipeline.run(
                source=str(video_path),
                sample_rate_fps=2.0,
                max_frames=6,
                use_tracking=False,
                speed_limit=5.0,
                camera_id="camera-01",
                emit_speed_events=True,
                radar_speed=33.0,
                event_emitter=event_emitter,
                save_evidence=False,
            )

        self.assertEqual(result.generated_event_count, 1)
        self.assertEqual(len(event_emitter.calls), 1)
        self.assertEqual(result.generated_events[0].event_type, "speed.violation_alert")
        self.assertEqual(result.generated_events[0].camera_id, "camera-01")
        self.assertEqual(result.generated_events[0].gateway_status_code, 201)
        self.assertIsNotNone(result.generated_events[0].track_id)


if __name__ == "__main__":
    unittest.main()
