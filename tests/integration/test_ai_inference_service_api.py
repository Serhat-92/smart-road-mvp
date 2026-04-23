"""Integration-style tests for the ai-inference HTTP service."""

from __future__ import annotations

from base64 import b64encode
from pathlib import Path
import sys
import unittest

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]
AI_INFERENCE_ROOT = REPO_ROOT / "services" / "ai-inference"

ai_inference_root_str = str(AI_INFERENCE_ROOT)
if ai_inference_root_str not in sys.path:
    sys.path.insert(0, ai_inference_root_str)

from service_api import create_app
from src.ai_inference.utils import (
    BoundingBox,
    DetectionRecord,
    FrameDetectionResult,
    FrameMetadata,
    GeneratedEventRecord,
    SpeedEstimate,
    VideoDetectionResult,
)


class FakeAIInferenceService:
    def __init__(self):
        self.last_image_request = None
        self.last_video_request = None

    def analyze_image_bytes(self, image_bytes, **kwargs):
        self.last_image_request = {"size": len(image_bytes), **kwargs}
        return FrameDetectionResult(
            frame=FrameMetadata.from_dimensions(
                source=kwargs.get("source", "image-frame"),
                frame_index=kwargs.get("frame_index", 0),
                width=1280,
                height=720,
                timestamp_ms=kwargs.get("timestamp_ms"),
                sampled_fps=kwargs.get("sampled_fps"),
                source_fps=kwargs.get("source_fps"),
                captured_at=kwargs.get("captured_at"),
            ),
            detections=[
                DetectionRecord(
                    label="car",
                    confidence=0.91,
                    bounding_box=BoundingBox(x1=10.0, y1=20.0, x2=110.0, y2=220.0),
                    class_id=2,
                    track_id=17,
                )
            ],
        )

    def infer_video(self, **kwargs):
        self.last_video_request = kwargs
        frame_result = FrameDetectionResult(
            frame=FrameMetadata.from_dimensions(
                source=kwargs["source"],
                frame_index=0,
                width=1920,
                height=1080,
                sampled_fps=kwargs["sample_rate_fps"],
            ),
            detections=[
                DetectionRecord(
                    label="truck",
                    confidence=0.88,
                    bounding_box=BoundingBox(x1=50.0, y1=60.0, x2=300.0, y2=340.0),
                    class_id=7,
                    track_id=None,
                    speed_estimate=SpeedEstimate(
                        relative_speed_kmh=42.5,
                        calibration_factor=36.0,
                    ),
                )
            ],
        )
        return VideoDetectionResult(
            source=kwargs["source"],
            sample_rate_fps=kwargs["sample_rate_fps"],
            processed_frames=5,
            sampled_frames=1,
            source_fps=25.0,
            frames=[frame_result],
            generated_events=[
                GeneratedEventRecord(
                    event_type="speed.violation_alert",
                    camera_id=kwargs.get("camera_id") or "camera-01",
                    timestamp="2026-04-22T12:00:00+00:00",
                    track_id=23,
                    estimated_speed=42.5,
                    radar_speed=44.0,
                    confidence_score=0.88,
                    image_evidence_path="datasets/evidence/camera-01/track-23.jpg",
                    delivery_status="sent",
                    gateway_event_id="evt-123",
                    gateway_status_code=201,
                )
            ],
        )


class FakeRadarFusion:
    def fuse_speed_violation_event(
        self,
        radar_reading,
        vehicle_tracks,
        speed_limit,
        patrol_speed=0.0,
        patrol_accel=0.0,
    ):
        del radar_reading
        del vehicle_tracks
        del speed_limit
        del patrol_speed
        del patrol_accel

        class _Event:
            def to_payload(self):
                return {
                    "event_type": "speed_violation",
                    "matched": True,
                    "estimated_speed": 84.0,
                    "radar_speed": 88.0,
                    "road_speed_limit": 70.0,
                    "confidence_score": 0.82,
                }

        return _Event()


class FakeAppState:
    def __init__(self):
        self.settings = type("Settings", (), {"environment": "test", "lazy_model_load": True, "model_path": "fake.pt"})()
        self.model_loaded = False
        self.radar_fusion = FakeRadarFusion()
        self.event_emitter = object()
        self.service = FakeAIInferenceService()

    def get_service(self):
        self.model_loaded = True
        return self.service


class AIInferenceServiceApiTests(unittest.TestCase):
    def test_frame_analyze_upload_returns_structured_detections(self):
        app = create_app(state=FakeAppState())

        with TestClient(app) as client:
            response = client.post(
                "/frame/analyze",
                files={"file": ("frame.jpg", b"fake-image-bytes", "image/jpeg")},
                data={"source": "cam-01", "frame_index": 7, "use_tracking": "true"},
            )

            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body["frame"]["source"], "cam-01")
            self.assertEqual(body["frame"]["frame_index"], 7)
            self.assertEqual(body["detection_count"], 1)
            self.assertEqual(body["detections"][0]["label"], "car")
            self.assertEqual(body["detections"][0]["bounding_box"]["x2"], 110.0)

    def test_frame_analyze_base64_returns_structured_detections(self):
        app = create_app(state=FakeAppState())

        with TestClient(app) as client:
            response = client.post(
                "/frame/analyze/base64",
                json={
                    "frame_base64": b64encode(b"fake-image-bytes").decode("ascii"),
                    "source": "rtsp://cam-02",
                    "frame_index": 3,
                },
            )

            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body["frame"]["source"], "rtsp://cam-02")
            self.assertEqual(body["detections"][0]["track_id"], 17)

    def test_video_analyze_returns_structured_frames(self):
        app = create_app(state=FakeAppState())

        with TestClient(app) as client:
            response = client.post(
                "/video/analyze",
                json={
                    "source": "sample.mp4",
                    "sample_rate_fps": 2.0,
                    "max_frames": 5,
                    "use_tracking": False,
                    "camera_id": "camera-01",
                    "speed_limit": 35.0,
                    "emit_speed_events": True,
                    "radar_speed": 44.0,
                },
            )

            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body["processed_frames"], 5)
            self.assertEqual(body["total_detections"], 1)
            self.assertEqual(body["generated_event_count"], 1)
            self.assertEqual(body["generated_events"][0]["event_type"], "speed.violation_alert")
            self.assertEqual(body["generated_events"][0]["camera_id"], "camera-01")
            self.assertEqual(body["generated_events"][0]["gateway_status_code"], 201)
            self.assertEqual(body["frames"][0]["detections"][0]["label"], "truck")
            self.assertEqual(
                body["frames"][0]["detections"][0]["speed_estimate"]["relative_speed_kmh"],
                42.5,
            )
            self.assertTrue(
                body["frames"][0]["detections"][0]["speed_estimate"]["is_approximate"]
            )

    def test_radar_fuse_allows_simulated_input(self):
        app = create_app(state=FakeAppState())

        with TestClient(app) as client:
            response = client.post(
                "/radar/fuse",
                json={
                    "vehicle_tracks": {
                        "7": {
                            "speed": 84.0,
                            "box": [10, 20, 110, 220],
                            "label": "car",
                            "confidence": 0.91,
                        }
                    },
                    "speed_limit": 70.0,
                    "patrol_speed": 0.0,
                    "patrol_accel": 0.0,
                },
            )

            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body["event_type"], "speed_violation")
            self.assertEqual(body["estimated_speed"], 84.0)
            self.assertEqual(body["radar_speed"], 88.0)
            self.assertEqual(body["road_speed_limit"], 70.0)


if __name__ == "__main__":
    unittest.main()
