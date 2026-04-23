"""Integration tests for speed violation evidence generation."""

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

from src.ai_inference.eventing import EvidenceStore, SpeedViolationEventEmitter
from src.ai_inference.utils import BoundingBox, DetectionRecord, FrameMetadata, SpeedEstimate


class EvidenceGenerationTests(unittest.TestCase):
    def test_evidence_store_saves_annotated_full_frame(self):
        frame = np.zeros((120, 180, 3), dtype=np.uint8)
        frame[:, :] = (12, 18, 24)
        bounding_box = BoundingBox(x1=30.0, y1=25.0, x2=120.0, y2=95.0)

        with tempfile.TemporaryDirectory() as temp_dir:
            store = EvidenceStore(temp_dir)
            saved_path = store.save_detection_evidence(
                frame=frame,
                camera_id="cam-annotated-01",
                track_id=7,
                frame_index=4,
                timestamp_ms=800.0,
                bounding_box=bounding_box,
                estimated_speed=84.5,
                radar_speed=82.0,
            )

            self.assertIsNotNone(saved_path)
            saved_file = Path(saved_path)
            self.assertTrue(saved_file.exists())

            annotated = cv2.imread(str(saved_file))
            self.assertIsNotNone(annotated)
            self.assertEqual(tuple(annotated.shape), tuple(frame.shape))
            self.assertGreater(int(np.abs(annotated.astype(np.int16) - frame.astype(np.int16)).sum()), 0)

    def test_emitter_includes_annotated_evidence_path_in_event_payload(self):
        frame = np.zeros((140, 220, 3), dtype=np.uint8)
        frame[:, :] = (30, 30, 30)

        detection = DetectionRecord(
            label="car",
            confidence=0.92,
            bounding_box=BoundingBox(x1=40.0, y1=35.0, x2=170.0, y2=110.0),
            class_id=2,
            track_id=11,
            speed_estimate=SpeedEstimate(relative_speed_kmh=86.4, calibration_factor=36.0),
        )
        frame_metadata = FrameMetadata.from_dimensions(
            source="datasets/samples/test.mp4",
            frame_index=6,
            width=220,
            height=140,
            timestamp_ms=1200.0,
            sampled_fps=5.0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            emitter = SpeedViolationEventEmitter(evidence_store=EvidenceStore(temp_dir))
            event_record = emitter.emit_speed_violation(
                frame_metadata=frame_metadata,
                detection=detection,
                frame=frame,
                camera_id="cam-evidence-02",
                speed_limit=70.0,
                radar_speed=82.1,
                save_evidence=True,
            )

            self.assertIsNotNone(event_record)
            self.assertIsNotNone(event_record.image_evidence_path)
            self.assertEqual(
                event_record.image_evidence_path,
                event_record.payload["image_evidence_path"],
            )
            self.assertTrue(Path(event_record.image_evidence_path).exists())
            self.assertEqual(event_record.payload["track_id"], 11)
            self.assertEqual(event_record.payload["estimated_speed"], 86.4)
            self.assertEqual(event_record.payload["radar_speed"], 82.1)


if __name__ == "__main__":
    unittest.main()
