"""Evaluate YOLOv8 detections on the sample bus video.

This script is intentionally stored under ``notebooks/`` but implemented as a
plain Python entrypoint so it can be run without Jupyter:

    python notebooks/model_evaluation.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_INFERENCE_SRC = REPO_ROOT / "services" / "ai-inference" / "src"

if str(AI_INFERENCE_SRC) not in sys.path:
    sys.path.insert(0, str(AI_INFERENCE_SRC))

from ai_inference.detector import VehicleDetector


VIDEO_PATH = REPO_ROOT / "datasets" / "samples" / "bus-sample.mp4"
OUTPUT_DIR = REPO_ROOT / "datasets" / "evaluation"
OUTPUT_PATH = OUTPUT_DIR / "model_eval_results.json"


def resolve_model_path() -> str:
    local_model = REPO_ROOT / "yolov8n.pt"
    if local_model.exists():
        return str(local_model)
    return "yolov8n.pt"


def main() -> int:
    if not VIDEO_PATH.exists():
        raise SystemExit(f"Sample video not found: {VIDEO_PATH}")

    try:
        import cv2
    except ImportError as exc:  # pragma: no cover - runtime dependency
        raise SystemExit("OpenCV is required to run model evaluation.") from exc

    detector = VehicleDetector(model_path=resolve_model_path())
    capture = cv2.VideoCapture(str(VIDEO_PATH))
    if not capture.isOpened():
        raise SystemExit(f"Unable to open video: {VIDEO_PATH}")

    frame_results: list[dict] = []
    class_confidences: dict[str, list[float]] = defaultdict(list)
    frames_with_detections = 0
    total_frames = 0
    highest_confidence_frame: dict | None = None
    lowest_confidence_frame: dict | None = None

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            raw_result = detector.detect(frame)
            detections = detector.to_structured_detections(raw_result)
            total_frames += 1

            frame_detection_payloads = []
            if detections:
                frames_with_detections += 1

            frame_confidences = []
            for detection in detections:
                confidence = float(detection.confidence)
                frame_confidences.append(confidence)
                class_confidences[detection.label].append(confidence)
                frame_detection_payloads.append(
                    {
                        "class": detection.label,
                        "confidence": confidence,
                        "bbox": {
                            "x1": detection.bounding_box.x1,
                            "y1": detection.bounding_box.y1,
                            "x2": detection.bounding_box.x2,
                            "y2": detection.bounding_box.y2,
                        },
                    }
                )

            frame_record = {
                "frame_index": total_frames - 1,
                "detection_count": len(frame_detection_payloads),
                "detections": frame_detection_payloads,
            }
            frame_results.append(frame_record)

            if frame_confidences:
                frame_max_confidence = max(frame_confidences)
                frame_min_confidence = min(frame_confidences)

                if (
                    highest_confidence_frame is None
                    or frame_max_confidence > highest_confidence_frame["confidence"]
                ):
                    highest_confidence_frame = {
                        "frame_index": frame_record["frame_index"],
                        "confidence": frame_max_confidence,
                        "detection_count": frame_record["detection_count"],
                    }

                if (
                    lowest_confidence_frame is None
                    or frame_min_confidence < lowest_confidence_frame["confidence"]
                ):
                    lowest_confidence_frame = {
                        "frame_index": frame_record["frame_index"],
                        "confidence": frame_min_confidence,
                        "detection_count": frame_record["detection_count"],
                    }
    finally:
        capture.release()

    class_avg_confidence = {
        label: round(sum(values) / len(values), 4) for label, values in sorted(class_confidences.items())
    }

    result = {
        "video_path": str(VIDEO_PATH),
        "model_path": resolve_model_path(),
        "total_frames": total_frames,
        "frames_with_detections": frames_with_detections,
        "class_avg_confidence": class_avg_confidence,
        "highest_confidence_frame": highest_confidence_frame,
        "lowest_confidence_frame": lowest_confidence_frame,
        "frames": frame_results,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Model evaluation summary")
    print("------------------------")
    print(f"Video:                    {VIDEO_PATH}")
    print(f"Model:                    {result['model_path']}")
    print(f"Total frames:             {total_frames}")
    print(f"Frames with detections:   {frames_with_detections}")
    print("Average confidence by class:")
    if class_avg_confidence:
        for label, avg_confidence in class_avg_confidence.items():
            print(f"  - {label}: {avg_confidence:.4f}")
    else:
        print("  - No detections recorded")

    if highest_confidence_frame is not None:
        print(
            "Highest confidence frame: "
            f"{highest_confidence_frame['frame_index']} "
            f"({highest_confidence_frame['confidence']:.4f})"
        )
    else:
        print("Highest confidence frame: none")

    if lowest_confidence_frame is not None:
        print(
            "Lowest confidence frame:  "
            f"{lowest_confidence_frame['frame_index']} "
            f"({lowest_confidence_frame['confidence']:.4f})"
        )
    else:
        print("Lowest confidence frame:  none")

    print(f"Results written to:       {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
