"""Integration tests for gateway speed violation event ingestion."""

from pathlib import Path
import sys
import unittest

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]
GATEWAY_API_ROOT = REPO_ROOT / "services" / "gateway-api"

gateway_api_root_str = str(GATEWAY_API_ROOT)
if gateway_api_root_str not in sys.path:
    sys.path.insert(0, gateway_api_root_str)

from app.main import app
from event_contracts import BoundingBox, RadarReading, SpeedViolationAlert, VisualTrack


def model_to_dict(instance):
    if hasattr(instance, "model_dump"):
        return instance.model_dump(mode="json")
    return instance.dict()


class GatewaySpeedViolationEventIntegrationTests(unittest.TestCase):
    def build_speed_violation_payload(self) -> dict:
        contract = SpeedViolationAlert(
            source_service="ai-inference-service",
            timestamp="2026-04-22T12:00:00Z",
            camera_id="cam-07",
            severity="warning",
            matched=True,
            confidence_score=0.93,
            speed_limit=70.0,
            estimated_speed=84.0,
            radar_speed=82.3,
            fused_speed=83.15,
            violation_amount=13.15,
            track_id=11,
            label="car",
            radar=RadarReading(
                source="pipeline-optional-radar",
                reading_id="r-11",
                relative_speed=82.3,
                absolute_speed=82.3,
                signal_confidence=0.5,
                timestamp_ms=1200.0,
            ),
            visual=VisualTrack(
                track_id=11,
                label="car",
                speed=84.0,
                confidence=0.93,
                bounding_box=BoundingBox(x1=15.0, y1=30.0, x2=180.0, y2=250.0),
            ),
            image_evidence_path="datasets/evidence/cam-07/cam-07_track-11_0000001200.jpg",
            metadata={
                "frame_index": 24,
                "frame_source": "datasets/samples/bus-sample.mp4",
            },
        )
        return model_to_dict(contract)

    def test_gateway_receives_speed_violation_alert(self):
        request_payload = {
            "event_type": "speed.violation_alert",
            "device_id": "cam-07",
            "severity": "warning",
            "payload": self.build_speed_violation_payload(),
            "occurred_at": "2026-04-22T12:00:00Z",
        }

        with TestClient(app) as client:
            token_response = client.post("/auth/token", data={"username": "admin", "password": "admin123"})
            token = token_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            response = client.post("/events", json=request_payload, headers=headers)
            self.assertEqual(response.status_code, 201, response.text)

            body = response.json()
            self.assertEqual(body["event_type"], "speed.violation_alert")
            self.assertEqual(body["device_id"], "cam-07")
            self.assertEqual(body["payload"]["camera_id"], "cam-07")
            self.assertEqual(body["payload"]["estimated_speed"], 84.0)
            self.assertEqual(body["payload"]["image_evidence_path"], request_payload["payload"]["image_evidence_path"])

            list_response = client.get("/events", headers=headers)
            self.assertEqual(list_response.status_code, 200, list_response.text)
            list_body = list_response.json()
            self.assertGreaterEqual(list_body["total"], 1)
            self.assertEqual(list_body["items"][0]["payload"]["track_id"], 11)


if __name__ == "__main__":
    unittest.main()
