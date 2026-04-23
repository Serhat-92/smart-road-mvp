"""Tests for MVP radar fusion and simulated radar input."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
AI_INFERENCE_ROOT = REPO_ROOT / "services" / "ai-inference"

ai_inference_root_str = str(AI_INFERENCE_ROOT)
if ai_inference_root_str not in sys.path:
    sys.path.insert(0, ai_inference_root_str)

from src.ai_inference.radar_fusion import RadarEventFusion, RadarSpeedSimulator


class RadarFusionMVPTests(unittest.TestCase):
    def test_simulator_creates_reading_from_fastest_track(self):
        simulator = RadarSpeedSimulator()
        vehicle_tracks = {
            1: {
                "label": "car",
                "confidence": 0.81,
                "speed_estimate": {"relative_speed_kmh": 64.0},
            },
            2: {
                "label": "truck",
                "confidence": 0.93,
                "speed_estimate": {"relative_speed_kmh": 88.0},
            },
        }

        reading = simulator.simulate(vehicle_tracks=vehicle_tracks, patrol_speed=10.0)

        self.assertGreater(reading.absolute_speed, 80.0)
        self.assertGreater(reading.relative_speed, 70.0)
        self.assertTrue(reading.source.startswith("simulated-radar"))

    def test_fusion_builds_speed_violation_event_with_simulated_radar(self):
        fusion = RadarEventFusion(min_violation_confidence=0.4)
        vehicle_tracks = {
            11: {
                "label": "car",
                "confidence": 0.95,
                "box": [15.0, 30.0, 180.0, 250.0],
                "speed_estimate": {"relative_speed_kmh": 96.0},
            },
            12: {
                "label": "truck",
                "confidence": 0.72,
                "box": [220.0, 40.0, 420.0, 280.0],
                "speed_estimate": {"relative_speed_kmh": 54.0},
            },
        }

        event = fusion.fuse_speed_violation_event(
            radar_reading=None,
            vehicle_tracks=vehicle_tracks,
            speed_limit=70.0,
            patrol_speed=0.0,
            patrol_accel=0.0,
        )
        payload = event.to_payload()

        self.assertEqual(payload["event_type"], "speed_violation")
        self.assertEqual(payload["road_speed_limit"], 70.0)
        self.assertGreater(payload["radar_speed"], 0.0)
        self.assertGreater(payload["estimated_speed"], 0.0)
        self.assertGreater(payload["confidence_score"], 0.4)
        self.assertEqual(payload["metadata"]["radar_mode"], "simulated")

    def test_fusion_uses_hardware_radar_when_available(self):
        fusion = RadarEventFusion()
        vehicle_tracks = {
            5: {
                "label": "car",
                "confidence": 0.91,
                "box": [10.0, 20.0, 110.0, 180.0],
                "speed_estimate": {"relative_speed_kmh": 82.0},
            }
        }

        event = fusion.fuse_speed_violation_event(
            radar_reading={
                "relative_speed": 84.0,
                "patrol_speed": 0.0,
                "signal_confidence": 0.9,
                "source": "hardware-radar",
            },
            vehicle_tracks=vehicle_tracks,
            speed_limit=70.0,
        )
        payload = event.to_payload()

        self.assertEqual(payload["source"], "hardware-radar")
        self.assertEqual(payload["metadata"]["radar_mode"], "hardware")
        self.assertEqual(payload["event_type"], "speed_violation")


if __name__ == "__main__":
    unittest.main()
