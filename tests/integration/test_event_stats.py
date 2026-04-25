"""Integration tests for event statistics endpoint."""

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


class EventStatsIntegrationTests(unittest.TestCase):
    def test_stats_returns_zero_when_no_events(self):
        with TestClient(app) as client:
            client.app.state.container.event_service.repository._items.clear()
            token_response = client.post("/auth/token", data={"username": "admin", "password": "admin123"})
            headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
            
            resp = client.get("/events/stats", headers=headers)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["total_events"], 0)
            self.assertEqual(data["pending_count"], 0)
            self.assertIsNone(data["avg_radar_speed"])
            self.assertIsNone(data["avg_estimated_speed"])

    def _get_valid_payload(self, device_id="cam-01"):
        return {
            "event_type": "test.event",
            "device_id": device_id,
            "severity": "critical",
            "payload": {
                "event_type": "speed_violation",
                "source_service": "ai-inference-service",
                "timestamp": "2026-04-22T12:00:00Z",
                "camera_id": device_id,
                "severity": "critical",
                "matched": True,
                "confidence_score": 0.95,
                "speed_limit": 70.0,
                "estimated_speed": 92.0,
                "radar_speed": 95.5,
                "fused_speed": 95.5,
                "violation_amount": 25.5,
                "track_id": 11,
                "label": "car",
                "radar": {
                    "source": "sim",
                    "reading_id": "r-1",
                    "relative_speed": 95.5,
                    "absolute_speed": 95.5,
                    "signal_confidence": 0.9,
                    "timestamp_ms": 1200.0,
                },
                "visual": {
                    "track_id": 11,
                    "label": "car",
                    "speed": 92.0,
                    "confidence": 0.95,
                    "bounding_box": {"x1": 0, "y1": 0, "x2": 1, "y2": 1},
                },
                "image_evidence_path": "path.jpg",
                "metadata": {}
            },
            "occurred_at": "2026-04-25T12:00:00Z"
        }

    def test_stats_counts_after_event_created(self):
        with TestClient(app) as client:
            client.app.state.container.event_service.repository._items.clear()
            token_response = client.post("/auth/token", data={"username": "admin", "password": "admin123"})
            headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
            
            client.post("/events", json=self._get_valid_payload("cam-01"), headers=headers)
            
            resp = client.get("/events/stats", headers=headers)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["total_events"], 1)
            self.assertEqual(data["pending_count"], 1)
            self.assertEqual(data["critical_count"], 1)
            self.assertAlmostEqual(data["avg_radar_speed"], 95.5)

    def test_stats_counts_after_status_update(self):
        with TestClient(app) as client:
            client.app.state.container.event_service.repository._items.clear()
            token_response = client.post("/auth/token", data={"username": "admin", "password": "admin123"})
            headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
            
            resp = client.post("/events", json=self._get_valid_payload("cam-01"), headers=headers)
            event_id = resp.json()["id"]
            
            client.patch(f"/events/{event_id}/status", json={"status": "reviewed"}, headers=headers)
            
            resp = client.get("/events/stats", headers=headers)
            data = resp.json()
            self.assertEqual(data["reviewed_count"], 1)
            self.assertEqual(data["pending_count"], 0)

    def test_stats_top_cameras(self):
        with TestClient(app) as client:
            client.app.state.container.event_service.repository._items.clear()
            token_response = client.post("/auth/token", data={"username": "admin", "password": "admin123"})
            headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
            
            for cid in ["cam-A", "cam-A", "cam-B"]:
                client.post("/events", json=self._get_valid_payload(cid), headers=headers)
                
            resp = client.get("/events/stats", headers=headers)
            data = resp.json()
            
            top_cameras = data["top_cameras"]
            self.assertGreater(len(top_cameras), 0)
            self.assertEqual(top_cameras[0]["camera_id"], "cam-A")
            self.assertEqual(top_cameras[0]["count"], 2)


if __name__ == "__main__":
    unittest.main()
