"""Integration tests for device persistence endpoints."""

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


class DevicePersistenceIntegrationTests(unittest.TestCase):
    """Tests for /devices endpoints with JWT authentication."""

    def _get_auth_headers(self, client):
        """Helper to obtain a valid JWT token and return auth headers."""
        response = client.post(
            "/auth/token",
            data={"username": "admin", "password": "admin123"},
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_create_device_with_token_returns_201(self):
        """POST /devices with valid token → 201."""
        with TestClient(app) as client:
            headers = self._get_auth_headers(client)
            response = client.post(
                "/devices",
                json={
                    "device_id": "cam-test-01",
                    "name": "Test Camera Alpha",
                    "kind": "camera",
                    "status": "active",
                    "metadata": {"zone": "test-zone"},
                },
                headers=headers,
            )
            self.assertEqual(response.status_code, 201, response.text)
            body = response.json()
            self.assertEqual(body["device_id"], "cam-test-01")
            self.assertEqual(body["name"], "Test Camera Alpha")

    def test_list_devices_returns_registered_device(self):
        """GET /devices returns previously registered device."""
        with TestClient(app) as client:
            headers = self._get_auth_headers(client)

            # Register a device first
            client.post(
                "/devices",
                json={
                    "device_id": "cam-list-test-01",
                    "name": "List Test Camera",
                    "kind": "camera",
                    "status": "active",
                    "metadata": {},
                },
                headers=headers,
            )

            # List devices
            response = client.get("/devices", headers=headers)
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertGreaterEqual(body["total"], 1)

            device_ids = [item["device_id"] for item in body["items"]]
            self.assertIn("cam-list-test-01", device_ids)

    def test_upsert_same_device_id_succeeds(self):
        """POST /devices with same device_id twice → upsert works, returns 200 or 201."""
        with TestClient(app) as client:
            headers = self._get_auth_headers(client)

            first_response = client.post(
                "/devices",
                json={
                    "device_id": "cam-upsert-01",
                    "name": "Upsert Camera Original",
                    "kind": "camera",
                    "status": "active",
                    "metadata": {"version": "v1"},
                },
                headers=headers,
            )
            self.assertIn(first_response.status_code, (200, 201), first_response.text)

            second_response = client.post(
                "/devices",
                json={
                    "device_id": "cam-upsert-01",
                    "name": "Upsert Camera Updated",
                    "kind": "camera",
                    "status": "active",
                    "metadata": {"version": "v2"},
                },
                headers=headers,
            )
            self.assertIn(second_response.status_code, (200, 201), second_response.text)

            body = second_response.json()
            self.assertEqual(body["device_id"], "cam-upsert-01")

    def test_create_device_without_token_returns_403(self):
        """POST /devices without token → 403."""
        with TestClient(app) as client:
            response = client.post(
                "/devices",
                json={
                    "device_id": "cam-noauth-01",
                    "name": "No Auth Camera",
                    "kind": "camera",
                    "status": "active",
                    "metadata": {},
                },
            )
            self.assertEqual(response.status_code, 403, response.text)


if __name__ == "__main__":
    unittest.main()
