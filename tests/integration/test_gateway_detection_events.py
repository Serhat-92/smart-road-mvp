"""Integration tests for gateway detection event ingestion."""

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
from event_contracts import BoundingBox, Detection, DetectionEvent, FrameMetadata


def model_to_dict(instance):
    if hasattr(instance, "model_dump"):
        return instance.model_dump(mode="json")
    return instance.dict()


class GatewayDetectionEventIntegrationTests(unittest.TestCase):
    def build_detection_event(self) -> dict:
        contract = DetectionEvent(
            source_service="ai-inference",
            frame=FrameMetadata(
                source="rtsp://north-belt-cam-01",
                frame_index=12,
                timestamp_ms=1200.0,
                source_fps=24.0,
                width=1920,
                height=1080,
                sampled_fps=2.0,
            ),
            detections=[
                Detection(
                    label="car",
                    confidence=0.94,
                    bounding_box=BoundingBox(x1=120.0, y1=80.0, x2=420.0, y2=360.0),
                    class_id=2,
                    track_id=17,
                )
            ],
            metadata={
                "device_id": "cam-03",
                "zone": "north-belt",
            },
        )
        return model_to_dict(contract)

    def build_gateway_event_request(self) -> dict:
        return {
            "event_type": "detection.event",
            "device_id": "cam-03",
            "severity": "warning",
            "payload": self.build_detection_event(),
            "occurred_at": "2026-04-22T12:00:00Z",
        }

    def test_gateway_receives_valid_detection_event_and_persists_it(self):
        with TestClient(app) as client:
            response = client.post("/events", json=self.build_gateway_event_request())
            self.assertEqual(response.status_code, 201, response.text)

            body = response.json()
            self.assertEqual(body["event_type"], "detection.event")
            self.assertEqual(body["device_id"], "cam-03")
            self.assertEqual(body["payload"]["event_type"], "detection.event")
            self.assertEqual(body["payload"]["frame"]["frame_index"], 12)
            self.assertEqual(body["payload"]["detections"][0]["label"], "car")

            list_response = client.get("/events")
            self.assertEqual(list_response.status_code, 200, list_response.text)
            list_body = list_response.json()
            self.assertEqual(list_body["total"], 1)
            self.assertEqual(list_body["items"][0]["payload"]["source_service"], "ai-inference")

            stored_records = client.app.state.container.event_service.repository.list()
            self.assertEqual(len(stored_records), 1)
            self.assertEqual(stored_records[0]["payload"]["metadata"]["zone"], "north-belt")
            self.assertEqual(stored_records[0]["payload"]["detections"][0]["track_id"], 17)

    def test_gateway_rejects_invalid_detection_event_schema(self):
        invalid_request = self.build_gateway_event_request()
        invalid_request["payload"]["frame"] = None
        invalid_request["payload"]["detections"][0]["confidence"] = 1.4

        with TestClient(app) as client:
            response = client.post("/events", json=invalid_request)
            self.assertEqual(response.status_code, 422, response.text)

            body = response.json()
            self.assertIn("error", body)
            self.assertEqual(body["error"]["code"], "invalid_event_payload")
            self.assertTrue(body["error"]["details"])
            self.assertIn("request_id", body)

            list_response = client.get("/events")
            self.assertEqual(list_response.status_code, 200, list_response.text)
            self.assertEqual(list_response.json()["total"], 0)


if __name__ == "__main__":
    unittest.main()
