"""Integration tests for demo seed data and evidence URL responses."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]
GATEWAY_API_ROOT = REPO_ROOT / "services" / "gateway-api"

gateway_api_root_str = str(GATEWAY_API_ROOT)
if gateway_api_root_str not in sys.path:
    sys.path.insert(0, gateway_api_root_str)

from app.core.config import get_settings
from app.main import create_app
from app.seed import seed_demo_data
from event_contracts import BoundingBox, RadarReading, SpeedViolationAlert, VisualTrack


def model_to_dict(instance):
    if hasattr(instance, "model_dump"):
        return instance.model_dump(mode="json")
    return instance.dict()


def auth_headers(client: TestClient) -> dict:
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def speed_violation_payload(image_evidence_path: str | None = None) -> dict:
    contract = SpeedViolationAlert(
        source_service="integration-test",
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
        image_evidence_path=image_evidence_path,
        metadata={"frame_index": 24},
    )
    return model_to_dict(contract)


def test_seed_loads_demo_events_when_enabled(monkeypatch):
    monkeypatch.setenv("GATEWAY_API_SEED_DEMO_DATA", "true")
    get_settings.cache_clear()

    try:
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/events", headers=auth_headers(client))

        assert response.status_code == 200, response.text
        assert response.json()["total"] >= 3
    finally:
        get_settings.cache_clear()


def test_seed_does_not_duplicate_on_restart(monkeypatch):
    monkeypatch.setenv("GATEWAY_API_SEED_DEMO_DATA", "true")
    get_settings.cache_clear()

    try:
        app = create_app()
        with TestClient(app) as client:
            container = client.app.state.container
            asyncio.run(seed_demo_data(container))

            response = client.get("/events", headers=auth_headers(client))

        assert response.status_code == 200, response.text
        assert response.json()["total"] == 3
    finally:
        get_settings.cache_clear()


def test_evidence_url_in_event_response(monkeypatch):
    monkeypatch.setenv("GATEWAY_API_SEED_DEMO_DATA", "false")
    get_settings.cache_clear()

    try:
        app = create_app()
        evidence_path = "datasets/evidence/cam-07/frame.jpg"
        request_payload = {
            "event_type": "speed.violation_alert",
            "device_id": "cam-07",
            "severity": "warning",
            "payload": speed_violation_payload(evidence_path),
            "occurred_at": "2026-04-22T12:00:00Z",
        }

        with TestClient(app) as client:
            headers = auth_headers(client)
            create_response = client.post("/events", json=request_payload, headers=headers)
            assert create_response.status_code == 201, create_response.text

            list_response = client.get("/events", headers=headers)

        assert list_response.status_code == 200, list_response.text
        item = list_response.json()["items"][0]
        assert item["image_evidence_path"] == evidence_path
        assert item["evidence_url"] == "/evidence/cam-07/frame.jpg"
    finally:
        get_settings.cache_clear()
