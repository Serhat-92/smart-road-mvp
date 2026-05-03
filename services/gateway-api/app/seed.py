import asyncio
from datetime import datetime, timedelta, timezone

from app.schemas.device import DeviceCreate
from app.schemas.event import EventCreate


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _speed_violation_payload(
    *,
    occurred_at: datetime,
    device_id: str,
    severity: str,
    estimated_speed: float,
    radar_speed: float,
    fused_speed: float,
    speed_limit: float,
    track_id: int,
    label: str,
    confidence_score: float,
    plate_number: str | None,
    violation_amount: float,
) -> dict:
    timestamp = occurred_at.isoformat()
    return {
        "schema_version": "1.0.0",
        "event_type": "speed.violation_alert",
        "source_service": "gateway-api-seed",
        "emitted_at": timestamp,
        "timestamp": timestamp,
        "camera_id": device_id,
        "severity": severity,
        "matched": True,
        "estimated_speed": estimated_speed,
        "radar_speed": radar_speed,
        "fused_speed": fused_speed,
        "speed_limit": speed_limit,
        "track_id": track_id,
        "label": label,
        "confidence_score": confidence_score,
        "plate_number": plate_number,
        "violation_amount": violation_amount,
        "metadata": {"seed": True},
    }


def _demo_events() -> list[dict]:
    now = _utc_now()
    return [
        {
            "event_type": "speed.violation_alert",
            "device_id": "demo-camera-01",
            "severity": "critical",
            "occurred_at": now - timedelta(minutes=5),
            "payload": _speed_violation_payload(
                occurred_at=now - timedelta(minutes=5),
                device_id="demo-camera-01",
                severity="critical",
                estimated_speed=2.21,
                radar_speed=85.5,
                fused_speed=61.0,
                speed_limit=1.0,
                track_id=1,
                label="bus",
                confidence_score=0.88,
                plate_number=None,
                violation_amount=500.0,
            ),
        },
        {
            "event_type": "speed.violation_alert",
            "device_id": "demo-camera-02",
            "severity": "warning",
            "occurred_at": now - timedelta(minutes=12),
            "payload": _speed_violation_payload(
                occurred_at=now - timedelta(minutes=12),
                device_id="demo-camera-02",
                severity="warning",
                estimated_speed=1.66,
                radar_speed=72.3,
                fused_speed=51.0,
                speed_limit=1.0,
                track_id=2,
                label="car",
                confidence_score=0.91,
                plate_number="34 ABC 123",
                violation_amount=300.0,
            ),
        },
        {
            "event_type": "speed.violation_alert",
            "device_id": "demo-camera-01",
            "severity": "critical",
            "occurred_at": now - timedelta(minutes=25),
            "payload": _speed_violation_payload(
                occurred_at=now - timedelta(minutes=25),
                device_id="demo-camera-01",
                severity="critical",
                estimated_speed=1.11,
                radar_speed=95.0,
                fused_speed=68.0,
                speed_limit=1.0,
                track_id=3,
                label="truck",
                confidence_score=0.79,
                plate_number="06 XYZ 456",
                violation_amount=750.0,
            ),
        },
    ]


DEMO_DEVICES = [
    {
        "device_id": "demo-camera-01",
        "name": "Kuzey Giris Kamerasi",
        "kind": "camera",
        "status": "active",
        "metadata": {"zone": "north", "rtsp_url": "rtsp://demo/stream1"},
    },
    {
        "device_id": "demo-camera-02",
        "name": "Guney Cikis Kamerasi",
        "kind": "camera",
        "status": "active",
        "metadata": {"zone": "south", "rtsp_url": "rtsp://demo/stream2"},
    },
    {
        "device_id": "radar-01",
        "name": "Ana Radar Sensoru",
        "kind": "radar",
        "status": "active",
        "metadata": {"zone": "north", "port": "/dev/ttyUSB0"},
    },
]


async def seed_demo_data(container) -> None:
    # Keep startup idempotent: if any events exist, assume the demo dataset is loaded.
    existing_events = container.event_service.list_events()
    if existing_events:
        return

    for device_data in DEMO_DEVICES:
        container.device_service.register_device(DeviceCreate(**device_data))

    for event_data in _demo_events():
        container.event_service.create_event(EventCreate(**event_data))

    await asyncio.sleep(0)
