"""Integration tests for camera calibration speed estimation."""

from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_INFERENCE_ROOT = REPO_ROOT / "services" / "ai-inference"

ai_inference_root_str = str(AI_INFERENCE_ROOT)
if ai_inference_root_str not in sys.path:
    sys.path.insert(0, ai_inference_root_str)

from src.ai_inference.pipelines.camera_calibration import CameraCalibration
from src.ai_inference.tracker.speed_tracker import ApproximateSpeedEstimator
from src.ai_inference.utils import BoundingBox, DetectionRecord


class CameraCalibrationTests(unittest.TestCase):
    def test_camera_calibration_pixels_to_meters(self):
        calib = CameraCalibration(pixels_per_meter=20.0)
        self.assertEqual(calib.pixels_to_meters(40.0), 2.0)

    def test_camera_calibration_speed_estimate(self):
        calib = CameraCalibration(pixels_per_meter=20.0)
        # 200 pixels -> 10 meters. 10 meters / 1.0 second = 10 m/s = 36 km/h.
        speed_kmh = calib.estimate_speed_kmh(pixel_distance=200.0, time_delta_seconds=1.0)
        self.assertAlmostEqual(speed_kmh, 36.0, places=1)

    def test_camera_calibration_from_reference_object(self):
        calib = CameraCalibration(reference_object_width_px=40, reference_object_width_m=2.0)
        self.assertEqual(calib.pixels_per_meter, 20.0)

    def test_speed_tracker_uses_calibration(self):
        calib = CameraCalibration(pixels_per_meter=20.0)
        tracker = ApproximateSpeedEstimator(calibration=calib)
        
        detections_1 = [
            DetectionRecord(
                label="car", confidence=0.9,
                bounding_box=BoundingBox(x1=10, y1=10, x2=50, y2=50),
                track_id=1
            )
        ]
        tracker.update(detections_1, timestamp_s=0.0)
        
        detections_2 = [
            DetectionRecord(
                label="car", confidence=0.9,
                bounding_box=BoundingBox(x1=10, y1=210, x2=50, y2=250), # moved 200 pixels
                track_id=1
            )
        ]
        result = tracker.update(detections_2, timestamp_s=1.0)
        
        self.assertIsNotNone(result[0].speed_estimate)
        self.assertIsNotNone(result[0].speed_estimate.relative_speed_kmh)
        self.assertAlmostEqual(result[0].speed_estimate.relative_speed_kmh, 36.0, places=1)

if __name__ == "__main__":
    unittest.main()
