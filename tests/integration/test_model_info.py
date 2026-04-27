"""Integration tests for the AI inference model info endpoint."""

from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]
AI_INFERENCE_ROOT = REPO_ROOT / "services" / "ai-inference"

ai_inference_root_str = str(AI_INFERENCE_ROOT)
if ai_inference_root_str not in sys.path:
    sys.path.insert(0, ai_inference_root_str)

ai_inference_src_str = str(AI_INFERENCE_ROOT / "src")
if ai_inference_src_str not in sys.path:
    sys.path.insert(0, ai_inference_src_str)

from service_api import create_app


class _FakeModel:
    device = "cpu"
    names = {0: "person", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
    pt_path = "/app/yolov8n.pt"


class _FakeDetector:
    def __init__(self):
        self.model = _FakeModel()
        self.vehicle_classes = [2, 7, 5, 3]
        self.image_size = 640

    @staticmethod
    def _resolve_label(names, class_id):
        if isinstance(names, dict):
            return str(names.get(class_id, class_id))
        return str(class_id)


class _FakeInferenceService:
    def __init__(self):
        self.detector = _FakeDetector()


class _FakeAppState:
    def __init__(self):
        self.settings = type(
            "Settings",
            (),
            {"environment": "test", "lazy_model_load": True, "model_path": "yolov8n.pt"},
        )()
        self.model_loaded = False
        self.radar_fusion = object()
        self.event_emitter = object()
        self.service = _FakeInferenceService()

    def get_service(self):
        self.model_loaded = True
        return self.service


def test_model_info_endpoint_returns_expected_fields():
    app = create_app(state=_FakeAppState())

    with TestClient(app) as client:
        response = client.get("/model/info")

    assert response.status_code == 200, response.text
    body = response.json()
    assert "model_name" in body
    assert "device" in body
    assert "vehicle_classes" in body
    assert body["model_name"] == "yolov8n"
    assert body["device"] == "cpu"
    assert isinstance(body["vehicle_classes"], list)
    assert body["vehicle_classes"]
