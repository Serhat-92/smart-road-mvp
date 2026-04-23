"""YOLO-based vehicle detector implementation."""

from pathlib import Path

from ..utils import BoundingBox, DetectionRecord
from ..utils.paths import resolve_repo_path


class YOLOVehicleDetector:
    """Wrap the repository's existing YOLOv8-based vehicle detection logic."""

    def __init__(
        self,
        model_path="yolov8n.pt",
        vehicle_classes=None,
        confidence=0.3,
        iou=0.5,
        image_size=640,
        tracker_config="bytetrack.yaml",
    ):
        resolved_model_path = self._resolve_model_path(model_path)
        print(f"Model yukleniyor: {resolved_model_path}...")
        try:
            from ultralytics import YOLO
        except ImportError as exc:  # pragma: no cover - optional Docker dependency
            raise RuntimeError(
                "Ultralytics is required for YOLO inference. Install the full "
                "AI dependencies or run the local demo script from the Python environment."
            ) from exc
        self.model = YOLO(resolved_model_path)
        self.vehicle_classes = vehicle_classes or [2, 3, 5, 7]
        self.confidence = confidence
        self.iou = iou
        self.image_size = image_size
        self.tracker_config = tracker_config

    @staticmethod
    def _resolve_model_path(model_path):
        path = Path(str(model_path)).expanduser()
        if path.is_absolute():
            return str(path)

        resolved_path = resolve_repo_path(path, must_exist=True)
        if resolved_path.exists() and resolved_path.is_file():
            return str(resolved_path)

        # Let Ultralytics resolve/download known model aliases such as yolov8n.pt.
        return str(model_path)

    def detect(self, frame):
        """Run one-shot detection without persistent tracking."""
        results = self.model(
            frame,
            classes=self.vehicle_classes,
            verbose=False,
            conf=self.confidence,
            iou=self.iou,
            imgsz=self.image_size,
        )
        return results[0]

    def detect_and_track(self, frame):
        """Run detection with persistent track IDs across frames."""
        results = self.model.track(
            frame,
            persist=True,
            classes=self.vehicle_classes,
            verbose=False,
            conf=self.confidence,
            iou=self.iou,
            imgsz=self.image_size,
            tracker=self.tracker_config,
        )
        return results[0]

    def to_structured_detections(self, result):
        """Convert an Ultralytics result into serializable detection records."""
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return []

        xyxy = boxes.xyxy.cpu().tolist() if boxes.xyxy is not None else []
        class_ids = boxes.cls.int().cpu().tolist() if boxes.cls is not None else []
        confidences = boxes.conf.cpu().tolist() if boxes.conf is not None else []
        track_ids = boxes.id.int().cpu().tolist() if boxes.id is not None else []
        names = getattr(result, "names", getattr(self.model, "names", {}))

        records = []
        for index, coordinates in enumerate(xyxy):
            class_id = class_ids[index] if index < len(class_ids) else None
            confidence = confidences[index] if index < len(confidences) else 0.0
            track_id = track_ids[index] if index < len(track_ids) else None
            label = self._resolve_label(names, class_id)

            records.append(
                DetectionRecord(
                    label=label,
                    confidence=float(confidence),
                    bounding_box=BoundingBox(
                        x1=float(coordinates[0]),
                        y1=float(coordinates[1]),
                        x2=float(coordinates[2]),
                        y2=float(coordinates[3]),
                    ),
                    class_id=class_id,
                    track_id=track_id,
                )
            )

        return records

    @staticmethod
    def _resolve_label(names, class_id):
        if class_id is None:
            return "unknown"
        if isinstance(names, dict):
            return str(names.get(class_id, class_id))
        if isinstance(names, (list, tuple)) and 0 <= class_id < len(names):
            return str(names[class_id])
        return str(class_id)


class VehicleDetector(YOLOVehicleDetector):
    """Backward-compatible alias for the service runtime."""
