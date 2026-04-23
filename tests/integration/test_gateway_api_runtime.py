"""Integration tests for gateway health, device, and ingest flows."""

from pathlib import Path
import asyncio
import sys
import unittest

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]
GATEWAY_API_ROOT = REPO_ROOT / "services" / "gateway-api"

gateway_api_root_str = str(GATEWAY_API_ROOT)
if gateway_api_root_str not in sys.path:
    sys.path.insert(0, gateway_api_root_str)

from app.db.session import DatabaseManager
from app.main import app
from app.core.config import Settings


class GatewayApiRuntimeIntegrationTests(unittest.TestCase):
    def test_health_devices_and_ingest_endpoints_work(self):
        with TestClient(app) as client:
            health_response = client.get("/health")
            self.assertEqual(health_response.status_code, 200, health_response.text)

            health_body = health_response.json()
            self.assertIn(health_body["status"], {"ok", "degraded"})
            self.assertEqual(health_body["storage"]["backend"], "memory")
            self.assertIn("request_id", health_body)

            device_response = client.post(
                "/devices",
                json={
                    "device_id": "cam-operator-01",
                    "name": "North Entrance Camera",
                    "kind": "camera",
                    "status": "active",
                    "metadata": {"zone": "north"},
                },
            )
            self.assertEqual(device_response.status_code, 201, device_response.text)
            self.assertEqual(device_response.json()["device_id"], "cam-operator-01")

            ingest_response = client.post(
                "/ingest/frame",
                json={
                    "device_id": "cam-operator-01",
                    "frame_id": "frame-0001",
                    "media_url": "rtsp://cam-operator-01/stream",
                    "width": 1920,
                    "height": 1080,
                    "metadata": {"lane": 2},
                },
            )
            self.assertEqual(ingest_response.status_code, 202, ingest_response.text)
            ingest_body = ingest_response.json()
            self.assertTrue(ingest_body["accepted"])
            self.assertTrue(ingest_body["known_device"])
            self.assertEqual(ingest_body["queue_status"], "queued")

            devices_response = client.get("/devices")
            self.assertEqual(devices_response.status_code, 200, devices_response.text)
            devices_body = devices_response.json()
            self.assertEqual(devices_body["total"], 1)
            self.assertEqual(devices_body["items"][0]["device_id"], "cam-operator-01")

    def test_postgres_unavailable_falls_back_to_memory(self):
        settings = Settings(
            app_name="gateway-api",
            version="0.1.0",
            environment="test",
            host="127.0.0.1",
            port=8080,
            log_level="INFO",
            cors_origins=("http://localhost:5173",),
            seed_demo_data=False,
            postgres_enabled=True,
            postgres_host="127.0.0.1",
            postgres_port=65432,
            postgres_user="postgres",
            postgres_password="postgres",
            postgres_database="gateway_api",
            postgres_echo=False,
            postgres_connect_timeout_seconds=1,
        )

        manager = DatabaseManager(settings=settings)
        asyncio.run(manager.connect())

        status_snapshot = manager.status_snapshot()
        storage_snapshot = manager.storage_status_snapshot()

        self.assertFalse(status_snapshot["connected"])
        self.assertEqual(status_snapshot["state"], "fallback")
        self.assertTrue(status_snapshot["last_error"])
        self.assertEqual(storage_snapshot["backend"], "memory")
        self.assertTrue(storage_snapshot["fallback_active"])

    def test_ingest_validation_errors_return_structured_response(self):
        with TestClient(app) as client:
            response = client.post(
                "/ingest/frame",
                json={
                    "device_id": "cam-bad-01",
                    "frame_id": "frame-bad-01",
                    "width": 1920,
                    "metadata": {"lane": 1},
                },
            )

            self.assertEqual(response.status_code, 422, response.text)
            body = response.json()
            self.assertEqual(body["error"]["code"], "invalid_ingest_request")
            self.assertTrue(body["error"]["details"])
            self.assertIn("request_id", body)


if __name__ == "__main__":
    unittest.main()
