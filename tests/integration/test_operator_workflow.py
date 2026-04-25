"""Integration tests for operator workflow (event status management)."""

from pathlib import Path
import sys
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]
GATEWAY_API_ROOT = REPO_ROOT / "services" / "gateway-api"

gateway_api_root_str = str(GATEWAY_API_ROOT)
if gateway_api_root_str not in sys.path:
    sys.path.insert(0, gateway_api_root_str)

from app.main import app


class OperatorWorkflowIntegrationTests(unittest.TestCase):
    """Tests for PATCH /events/{event_id}/status endpoint."""

    def _get_auth_headers(self, client):
        """Helper to obtain a valid JWT token and return auth headers."""
        response = client.post(
            "/auth/token",
            data={"username": "admin", "password": "admin123"},
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def _create_test_event(self, client, headers):
        """Helper to create a speed violation event and return the response body."""
        response = client.post(
            "/events",
            json={
                "event_type": "speed.violation_alert",
                "device_id": "cam-workflow-01",
                "severity": "warning",
                "payload": {
                    "event_type": "speed.violation_alert",
                    "source_service": "ai-inference",
                    "timestamp": "2026-04-25T12:00:00Z",
                    "camera_id": "cam-workflow-01",
                    "severity": "warning",
                    "matched": True,
                    "confidence_score": 0.9,
                    "speed_limit": 70.0,
                    "estimated_speed": 85.0,
                    "radar_speed": 83.0,
                    "fused_speed": 84.0,
                    "violation_amount": 14.0,
                    "track_id": 42,
                    "label": "car",
                    "image_evidence_path": "datasets/evidence/test.jpg",
                },
                "occurred_at": "2026-04-25T12:00:00Z",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        return response.json()

    def test_event_status_default_is_pending(self):
        """POST /events creates event with operator_status 'pending'."""
        with TestClient(app) as client:
            headers = self._get_auth_headers(client)
            body = self._create_test_event(client, headers)
            self.assertEqual(body["operator_status"], "pending")

    def test_patch_event_status_to_reviewed(self):
        """PATCH /events/{id}/status to 'reviewed' updates successfully."""
        with TestClient(app) as client:
            headers = self._get_auth_headers(client)
            event = self._create_test_event(client, headers)
            event_id = event["id"]

            response = client.patch(
                f"/events/{event_id}/status",
                json={"status": "reviewed"},
                headers=headers,
            )
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body["operator_status"], "reviewed")
            self.assertEqual(body["id"], event_id)

    def test_patch_event_status_to_dismissed(self):
        """PATCH /events/{id}/status to 'dismissed' updates successfully."""
        with TestClient(app) as client:
            headers = self._get_auth_headers(client)
            event = self._create_test_event(client, headers)
            event_id = event["id"]

            response = client.patch(
                f"/events/{event_id}/status",
                json={"status": "dismissed"},
                headers=headers,
            )
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body["operator_status"], "dismissed")

    def test_patch_event_status_invalid_value(self):
        """PATCH /events/{id}/status with invalid status → 422."""
        with TestClient(app) as client:
            headers = self._get_auth_headers(client)
            event = self._create_test_event(client, headers)
            event_id = event["id"]

            response = client.patch(
                f"/events/{event_id}/status",
                json={"status": "invalid_value"},
                headers=headers,
            )
            self.assertEqual(response.status_code, 422, response.text)

    def test_patch_nonexistent_event(self):
        """PATCH /events/{nonexistent_id}/status → 404."""
        with TestClient(app) as client:
            headers = self._get_auth_headers(client)
            fake_id = str(uuid4())

            response = client.patch(
                f"/events/{fake_id}/status",
                json={"status": "reviewed"},
                headers=headers,
            )
            self.assertEqual(response.status_code, 404, response.text)

    def test_patch_event_status_persists_in_list(self):
        """After PATCH, GET /events returns updated operator_status."""
        with TestClient(app) as client:
            headers = self._get_auth_headers(client)
            event = self._create_test_event(client, headers)
            event_id = event["id"]

            # Update to reviewed
            client.patch(
                f"/events/{event_id}/status",
                json={"status": "reviewed"},
                headers=headers,
            )

            # Verify in list
            list_response = client.get("/events", headers=headers)
            self.assertEqual(list_response.status_code, 200)
            items = list_response.json()["items"]
            matching = [e for e in items if e["id"] == event_id]
            self.assertEqual(len(matching), 1)
            self.assertEqual(matching[0]["operator_status"], "reviewed")


if __name__ == "__main__":
    unittest.main()
