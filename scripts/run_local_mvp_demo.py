"""Run the local MVP video-to-violation-event demo.

This script runs the AI inference pipeline in-process against a sample video and
sends generated speed violation events to the gateway API.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib import error, request


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_INFERENCE_SRC = REPO_ROOT / "services" / "ai-inference" / "src"

if str(AI_INFERENCE_SRC) not in sys.path:
    sys.path.insert(0, str(AI_INFERENCE_SRC))

from ai_inference.api import AIInferenceService
from ai_inference.eventing import EvidenceStore, GatewayEventPublisher, SpeedViolationEventEmitter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local MVP video detection, tracking, speed estimation, and event delivery.",
    )
    parser.add_argument(
        "--video",
        default=str(REPO_ROOT / "datasets" / "samples" / "bus-sample.mp4"),
        help="Local video file to process.",
    )
    parser.add_argument(
        "--gateway-url",
        default="http://127.0.0.1:8080",
        help="Gateway API base URL.",
    )
    parser.add_argument(
        "--camera-id",
        default="demo-camera-01",
        help="Camera/device id to include in generated events.",
    )
    parser.add_argument(
        "--speed-limit",
        type=float,
        default=1.0,
        help=(
            "Speed limit in km/h. Default is intentionally low so the bundled "
            "short sample video demonstrates event generation."
        ),
    )
    parser.add_argument(
        "--sample-rate-fps",
        type=float,
        default=5.0,
        help="Frame sampling rate for local video processing.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=8,
        help="Maximum source frames to read during the demo.",
    )
    parser.add_argument(
        "--model-path",
        default=str(REPO_ROOT / "yolov8n.pt"),
        help="YOLO model path.",
    )
    parser.add_argument(
        "--speed-factor",
        type=float,
        default=36.0,
        help="Approximate computer-vision speed calibration factor.",
    )
    parser.add_argument(
        "--radar-speed",
        type=float,
        default=None,
        help="Optional simulated/known radar speed to include in generated events.",
    )
    parser.add_argument(
        "--evidence-dir",
        default=str(REPO_ROOT / "datasets" / "evidence"),
        help="Directory where annotated violation evidence frames are saved.",
    )
    parser.add_argument(
        "--gateway-timeout",
        type=float,
        default=5.0,
        help="Gateway request timeout in seconds.",
    )
    parser.add_argument(
        "--allow-offline-gateway",
        action="store_true",
        help="Continue processing if the gateway API is unavailable.",
    )
    parser.add_argument(
        "--no-evidence",
        action="store_true",
        help="Do not save annotated evidence images.",
    )
    return parser.parse_args()


def ensure_file_exists(path: Path, label: str) -> None:
    if not path.exists() or not path.is_file():
        raise SystemExit(f"{label} not found: {path}")


def check_gateway_health(gateway_url: str, timeout_s: float) -> bool:
    health_url = gateway_url.rstrip("/") + "/health"
    try:
        with request.urlopen(health_url, timeout=timeout_s) as response:
            return 200 <= response.status < 300
    except (error.HTTPError, error.URLError, TimeoutError):
        return False


def print_demo_summary(result) -> None:
    print("\nDemo summary")
    print("------------")
    print(f"Processed frames: {result.processed_frames}")
    print(f"Sampled frames:   {result.sampled_frames}")
    print(f"Detections:       {result.total_detections}")
    print(f"Events generated: {result.generated_event_count}")

    for frame_result in result.frames:
        if not frame_result.detections:
            continue

        print(f"\nFrame {frame_result.frame.frame_index}")
        for detection in frame_result.detections:
            speed = None
            if detection.speed_estimate is not None:
                speed = detection.speed_estimate.relative_speed_kmh
            speed_text = f"{speed:.2f} km/h" if speed is not None else "n/a"
            print(
                "  "
                f"track={detection.track_id} "
                f"label={detection.label} "
                f"confidence={detection.confidence:.3f} "
                f"estimated_speed={speed_text}"
            )

    if not result.generated_events:
        print("\nNo speed violation events were generated.")
        return

    print("\nGenerated events")
    print("----------------")
    for event in result.generated_events:
        print(
            f"- {event.event_type} track={event.track_id} "
            f"estimated={event.estimated_speed} radar={event.radar_speed} "
            f"delivery={event.delivery_status} gateway_id={event.gateway_event_id}"
        )
        if event.image_evidence_path:
            print(f"  evidence={event.image_evidence_path}")


def main() -> int:
    args = parse_args()
    video_path = Path(args.video).expanduser().resolve()
    model_path = Path(args.model_path).expanduser().resolve()
    evidence_dir = Path(args.evidence_dir).expanduser().resolve()

    ensure_file_exists(video_path, "Video")
    ensure_file_exists(model_path, "YOLO model")

    gateway_available = check_gateway_health(args.gateway_url, args.gateway_timeout)
    if not gateway_available and not args.allow_offline_gateway:
        print(f"Gateway API is not reachable at {args.gateway_url}.")
        print("Start it first with:")
        print("$env:GATEWAY_API_HOST='127.0.0.1'; $env:GATEWAY_API_PORT='8080'; $env:POSTGRES_ENABLED='false'; python services/gateway-api/main.py")
        return 2

    if gateway_available:
        print(f"Gateway API reachable: {args.gateway_url}")
    else:
        print("Gateway API unavailable; continuing because --allow-offline-gateway was set.")

    print(f"Loading model: {model_path}")
    service = AIInferenceService(
        model_path=str(model_path),
        speed_factor=args.speed_factor,
    )
    event_emitter = SpeedViolationEventEmitter(
        publisher=GatewayEventPublisher(
            base_url=args.gateway_url,
            timeout_s=args.gateway_timeout,
        ),
        evidence_store=EvidenceStore(evidence_dir),
    )

    print(f"Processing video: {video_path}")
    result = service.infer_video(
        source=str(video_path),
        sample_rate_fps=args.sample_rate_fps,
        max_frames=args.max_frames,
        use_tracking=True,
        speed_limit=args.speed_limit,
        camera_id=args.camera_id,
        emit_speed_events=True,
        radar_speed=args.radar_speed,
        event_emitter=event_emitter,
        save_evidence=not args.no_evidence,
    )

    print_demo_summary(result)

    output = {
        "processed_frames": result.processed_frames,
        "sampled_frames": result.sampled_frames,
        "total_detections": result.total_detections,
        "generated_event_count": result.generated_event_count,
        "generated_events": [
            {
                "event_type": event.event_type,
                "track_id": event.track_id,
                "estimated_speed": event.estimated_speed,
                "radar_speed": event.radar_speed,
                "confidence_score": event.confidence_score,
                "delivery_status": event.delivery_status,
                "gateway_event_id": event.gateway_event_id,
                "gateway_status_code": event.gateway_status_code,
                "image_evidence_path": event.image_evidence_path,
            }
            for event in result.generated_events
        ],
    }
    print("\nMachine-readable result")
    print("-----------------------")
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
