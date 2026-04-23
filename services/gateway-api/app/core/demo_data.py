"""Optional local-development seed data for the gateway API."""

from datetime import datetime, timedelta, timezone

from app.core.pydantic import model_to_dict
from app.schemas.device import DeviceCreate
from app.schemas.event import EventCreate
from app.services.device_service import DeviceService
from app.services.event_service import EventService
from event_contracts import (
    BoundingBox,
    Detection,
    DetectionEvent,
    FrameMetadata,
    FusedVehicleEvent,
    RadarReading,
    SpeedViolationAlert,
    VisualTrack,
)


def seed_demo_data(
    device_service: DeviceService,
    event_service: EventService,
) -> None:
    """Populate in-memory repositories with demo records for local dev."""
    if device_service.list_devices() or event_service.list_events():
        return

    now = datetime.now(timezone.utc)

    demo_devices = [
        DeviceCreate(
            device_id="radar-07",
            name="Patrol Radar 07",
            kind="mobile-radar",
            status="active",
            metadata={
                "zone": "North Belt / Sector 4",
                "health": 98,
                "stream_state": "stable",
                "fps": 24,
                "latency_ms": 120,
                "battery": 81,
                "stream_source": "rtsp://north-belt-cam-01",
            },
        ),
        DeviceCreate(
            device_id="cam-03",
            name="Road Cam 03",
            kind="fixed-camera",
            status="active",
            metadata={
                "zone": "City Entry / Lane 2",
                "health": 94,
                "stream_state": "stable",
                "fps": 20,
                "latency_ms": 145,
                "battery": None,
                "stream_source": "rtsp://city-entry-cam-03",
            },
        ),
        DeviceCreate(
            device_id="radar-02",
            name="Bridge Radar 02",
            kind="bridge-radar",
            status="inactive",
            metadata={
                "zone": "Industrial Corridor",
                "health": 33,
                "stream_state": "unavailable",
                "fps": 0,
                "latency_ms": None,
                "battery": 19,
                "stream_source": "rtsp://bridge-radar-02",
            },
        ),
    ]

    for payload in demo_devices:
        device_service.register_device(payload)

    speed_alert = SpeedViolationAlert(
        source_service="ai-inference",
        emitted_at=now - timedelta(minutes=4),
        timestamp=now - timedelta(minutes=4, seconds=5),
        camera_id="radar-07",
        severity="critical",
        matched=True,
        confidence_score=0.94,
        speed_limit=90.0,
        estimated_speed=119.0,
        radar_speed=121.0,
        fused_speed=121.0,
        violation_amount=31.0,
        track_id=17,
        label="car",
        radar=RadarReading(
            source="radar-07",
            reading_id="reading-active-001",
            relative_speed=51.0,
            absolute_speed=121.0,
            patrol_speed=70.0,
            patrol_accel=0.2,
            signal_confidence=0.96,
            timestamp_ms=1713781200000.0,
        ),
        visual=VisualTrack(
            track_id=17,
            label="car",
            speed=119.0,
            confidence=0.92,
            bounding_box=BoundingBox(x1=120.0, y1=85.0, x2=420.0, y2=355.0),
        ),
        image_evidence_path="datasets/evidence/radar-07/radar-07_track-17_1713781200000.jpg",
        metadata={
            "location": "North Belt / Sector 4",
            "device_name": "Patrol Radar 07",
            "workflow_status": "escalated",
            "outcome": "ticket-issued",
        },
    )

    fused_event = FusedVehicleEvent(
        source_service="ai-inference",
        emitted_at=now - timedelta(minutes=9),
        matched=True,
        confidence_score=0.81,
        fusion_status="MATCHED",
        track_id=12,
        label="truck",
        radar=RadarReading(
            source="cam-03",
            reading_id="reading-history-002",
            relative_speed=17.0,
            absolute_speed=87.0,
            patrol_speed=70.0,
            patrol_accel=0.0,
            signal_confidence=0.85,
            timestamp_ms=1713780900000.0,
        ),
        visual=VisualTrack(
            track_id=12,
            label="truck",
            speed=84.0,
            confidence=0.8,
            bounding_box=BoundingBox(x1=260.0, y1=90.0, x2=610.0, y2=380.0),
        ),
        fused_speed=87.0,
        speed_delta=3.0,
        speed_limit=70.0,
        metadata={
            "location": "City Entry / Lane 2",
            "device_name": "Road Cam 03",
            "workflow_status": "review",
            "outcome": "validated",
        },
    )

    detection_event = DetectionEvent(
        source_service="ai-inference",
        emitted_at=now - timedelta(minutes=14),
        frame=FrameMetadata(
            source="rtsp://bridge-radar-02",
            frame_index=128,
            timestamp_ms=1713780600000.0,
            source_fps=20.0,
            width=1920,
            height=1080,
            sampled_fps=2.0,
        ),
        detections=[
            Detection(
                label="motorcycle",
                confidence=0.77,
                bounding_box=BoundingBox(x1=320.0, y1=140.0, x2=470.0, y2=430.0),
                class_id=3,
                track_id=31,
            )
        ],
        metadata={
            "location": "Industrial Corridor",
            "device_name": "Bridge Radar 02",
            "workflow_status": "dispatching",
            "outcome": "archived",
            "speed": 96.0,
            "speed_limit": 70.0,
        },
    )

    demo_events = [
        EventCreate(
            event_type=speed_alert.event_type,
            device_id="radar-07",
            severity="critical",
            payload=model_to_dict(speed_alert),
            occurred_at=speed_alert.emitted_at,
        ),
        EventCreate(
            event_type=fused_event.event_type,
            device_id="cam-03",
            severity="warning",
            payload=model_to_dict(fused_event),
            occurred_at=fused_event.emitted_at,
        ),
        EventCreate(
            event_type=detection_event.event_type,
            device_id="radar-02",
            severity="warning",
            payload=model_to_dict(detection_event),
            occurred_at=detection_event.emitted_at,
        ),
    ]

    for payload in demo_events:
        event_service.create_event(payload)
