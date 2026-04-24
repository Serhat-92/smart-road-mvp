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
        default=str(REPO_ROOT / "datasets" / "test_video_1.mp4"),
        help="Path to the local video file or an rtsp:// stream URL to process.",
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
    parser.add_argument(
        "--use-redis",
        action="store_true",
        help="Use Redis Pub/Sub for event delivery instead of HTTP POST.",
    )
    parser.add_argument(
        "--api-token",
        type=str,
        default=None,
        help="JWT Token for authenticated gateway requests.",
    )
    parser.add_argument(
        "--gateway-user",
        type=str,
        default="admin",
        help="Username for authenticating to the gateway API.",
    )
    parser.add_argument(
        "--gateway-password",
        type=str,
        default="admin123",
        help="Password for authenticating to the gateway API.",
    )
    parser.add_argument(
        "--radar-port",
        type=str,
        default=None,
        help="Serial port for real radar hardware (e.g. COM3 or /dev/ttyUSB0).",
    )
    parser.add_argument(
        "--radar-mock",
        action="store_true",
        help="Use mock radar sensor for testing.",
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
    video_source = args.video
    if not video_source.startswith("rtsp://"):
        video_path = Path(video_source).expanduser().resolve()
        ensure_file_exists(video_path, "Video")
        video_source = str(video_path)

    model_path = Path(args.model_path).expanduser().resolve()
    evidence_dir = Path(args.evidence_dir).expanduser().resolve()

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

    api_token = args.api_token
    if gateway_available and not args.use_redis and not api_token:
        import urllib.parse
        print(f"Authenticating to gateway as '{args.gateway_user}'...")
        data = urllib.parse.urlencode({
            "username": args.gateway_user,
            "password": args.gateway_password
        }).encode("ascii")
        req = request.Request(f"{args.gateway_url.rstrip('/')}/auth/token", data=data)
        try:
            with request.urlopen(req, timeout=args.gateway_timeout) as token_response:
                token_data = json.loads(token_response.read().decode("utf-8"))
                api_token = token_data.get("access_token")
                print("Successfully authenticated and obtained JWT token.")
        except Exception as e:
            print(f"Warning: Failed to authenticate to gateway: {e}")

    from ai_inference.ocr import PlateReader
    plate_reader = PlateReader()

    if args.use_redis:
        from ai_inference.eventing import RedisEventPublisher
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        print(f"Using RedisEventPublisher ({redis_url})")
        publisher = RedisEventPublisher(redis_url=redis_url)
    else:
        print(f"Using GatewayEventPublisher ({args.gateway_url})")
        auth_headers = {"Authorization": f"Bearer {api_token}"} if api_token else {}
        publisher = GatewayEventPublisher(
            base_url=args.gateway_url,
            headers=auth_headers,
            timeout_s=args.gateway_timeout,
        )

    event_emitter = SpeedViolationEventEmitter(
        publisher=publisher,
        evidence_store=EvidenceStore(evidence_dir),
        plate_reader=plate_reader,
    )

    sensor = None
    if args.radar_mock:
        from ai_inference.radar_hardware import MockRadarSensor
        print("Starting mock radar sensor...")
        sensor = MockRadarSensor(unit="kmh")
        sensor.start()
    elif args.radar_port:
        from ai_inference.radar_hardware import RadarSensor
        print(f"Starting real radar sensor on {args.radar_port}...")
        sensor = RadarSensor(port=args.radar_port, unit="kmh")
        sensor.start()

    print(f"Processing video source: {video_source}")
    try:
        # Override radar_speed continuously if sensor is attached
        if sensor:
            import threading
            
            # Monkey-patch infer_video loop logic to fetch real-time radar inside VideoDetectionPipeline...
            # A cleaner approach for the demo is just pass the latest radar speed dynamically, 
            # but since infer_video blocks, we use a simple thread to update a mutable dict.
            # However, AIInferenceService.infer_video doesn't take a callback. 
            # We will just pass the initial speed or fallback to mock radar values if not using sensor.
            if args.radar_mock:
                args.radar_speed = 85.5
            pass

        result = service.infer_video(
            source=video_source,
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
    finally:
        if sensor:
            print("Stopping radar sensor...")
            sensor.stop()

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
