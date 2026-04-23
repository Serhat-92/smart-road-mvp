"""Speed violation event generation and delivery helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
from typing import Any
from urllib import error, request
from uuid import uuid4

from ..utils import GeneratedEventRecord
from ..utils.paths import resolve_repo_path, to_repo_relative_path


logger = logging.getLogger("ai_inference.eventing")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class GatewayEventPublisher:
    """Send generated events to the gateway API without breaking the pipeline on failures."""

    def __init__(
        self,
        *,
        base_url: str | None,
        timeout_s: float = 5.0,
        opener=None,
    ):
        self.base_url = base_url.rstrip("/") if base_url else None
        self.timeout_s = float(timeout_s)
        self.opener = opener or request.urlopen

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    @property
    def events_url(self) -> str | None:
        if not self.base_url:
            return None
        return f"{self.base_url}/events"

    def publish(
        self,
        *,
        event_type: str,
        camera_id: str,
        occurred_at: str,
        severity: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.enabled or self.events_url is None:
            return {"delivery_status": "disabled"}

        request_body = {
            "event_type": event_type,
            "device_id": camera_id,
            "severity": severity,
            "payload": payload,
            "occurred_at": occurred_at,
        }
        encoded_body = json.dumps(request_body).encode("utf-8")
        http_request = request.Request(
            self.events_url,
            data=encoded_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with self.opener(http_request, timeout=self.timeout_s) as response:
                raw_response = response.read().decode("utf-8")
                parsed_response = json.loads(raw_response) if raw_response else {}
                return {
                    "delivery_status": "sent",
                    "gateway_status_code": response.status,
                    "gateway_event_id": parsed_response.get("id"),
                    "gateway_response": parsed_response,
                }
        except error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            logger.warning(
                "Gateway rejected violation event",
                extra={
                    "event_type": event_type,
                    "camera_id": camera_id,
                    "status_code": exc.code,
                },
            )
            return {
                "delivery_status": "failed",
                "gateway_status_code": exc.code,
                "gateway_error": response_body,
            }
        except error.URLError as exc:
            logger.warning(
                "Gateway connection failed",
                extra={"event_type": event_type, "camera_id": camera_id},
            )
            return {
                "delivery_status": "failed",
                "gateway_error": str(exc.reason),
            }


class EvidenceStore:
    """Persist annotated full-frame evidence when configured."""

    def __init__(self, root_dir: str | Path | None):
        self.root_dir = resolve_repo_path(root_dir) if root_dir else None

    def save_detection_evidence(
        self,
        *,
        frame,
        camera_id: str,
        track_id: int | None,
        frame_index: int,
        timestamp_ms: float | None,
        bounding_box,
        estimated_speed: float | None = None,
        radar_speed: float | None = None,
    ) -> str | None:
        if self.root_dir is None:
            return None

        try:
            import cv2
        except ImportError:  # pragma: no cover - runtime dependency
            return None

        safe_camera_id = self._sanitize_segment(camera_id)
        target_dir = self.root_dir / safe_camera_id
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp_segment = (
            f"{int(timestamp_ms):010d}" if timestamp_ms is not None else f"frame-{frame_index:06d}"
        )
        track_segment = track_id if track_id is not None else "na"
        file_path = target_dir / (
            f"{safe_camera_id}_track-{track_segment}_{timestamp_segment}.jpg"
        )

        annotated_frame = self._annotate_frame(
            frame=frame,
            track_id=track_id,
            bounding_box=bounding_box,
            estimated_speed=estimated_speed,
            radar_speed=radar_speed,
        )

        if not cv2.imwrite(str(file_path), annotated_frame):
            return None
        return to_repo_relative_path(file_path)

    @staticmethod
    def _sanitize_segment(value: str) -> str:
        sanitized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
        return sanitized.strip("-") or "camera"

    @staticmethod
    def _normalize_box(*, frame, bounding_box):
        frame_height, frame_width = frame.shape[:2]
        if bounding_box is None:
            return None

        x1 = max(int(round(bounding_box.x1)), 0)
        y1 = max(int(round(bounding_box.y1)), 0)
        x2 = min(int(round(bounding_box.x2)), frame_width - 1)
        y2 = min(int(round(bounding_box.y2)), frame_height - 1)

        if x2 <= x1 or y2 <= y1:
            return None
        return x1, y1, x2, y2

    @classmethod
    def _annotate_frame(
        cls,
        *,
        frame,
        track_id: int | None,
        bounding_box,
        estimated_speed: float | None,
        radar_speed: float | None,
    ):
        try:
            import cv2
        except ImportError:  # pragma: no cover - runtime dependency
            return frame

        annotated = frame.copy()
        normalized_box = cls._normalize_box(frame=annotated, bounding_box=bounding_box)
        if normalized_box is None:
            return annotated

        x1, y1, x2, y2 = normalized_box
        box_color = (0, 64, 255)
        text_color = (255, 255, 255)
        label_background = (8, 20, 48)

        cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 3)

        overlay_lines = [f"Track ID: {track_id if track_id is not None else 'n/a'}"]
        if estimated_speed is not None:
            overlay_lines.append(f"Est: {estimated_speed:.2f} km/h")
        if radar_speed is not None:
            overlay_lines.append(f"Radar: {radar_speed:.2f} km/h")

        text_x = x1 + 8
        baseline_y = max(y1 - 12, 28)
        line_height = 24
        box_height = (line_height * len(overlay_lines)) + 12
        top = max(baseline_y - box_height + 6, 0)
        bottom = min(baseline_y + 6, annotated.shape[0] - 1)
        right = min(x1 + 240, annotated.shape[1] - 1)
        cv2.rectangle(
            annotated,
            (x1, top),
            (right, bottom),
            label_background,
            thickness=-1,
        )

        for index, line in enumerate(overlay_lines):
            text_y = top + 22 + (index * line_height)
            cv2.putText(
                annotated,
                line,
                (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                text_color,
                2,
                cv2.LINE_AA,
            )
        return annotated


class SpeedViolationEventEmitter:
    """Create speed violation payloads and optionally deliver them to the gateway."""

    def __init__(
        self,
        *,
        publisher: GatewayEventPublisher | None = None,
        evidence_store: EvidenceStore | None = None,
        source_service: str = "ai-inference-service",
    ):
        self.publisher = publisher or GatewayEventPublisher(base_url=None)
        self.evidence_store = evidence_store or EvidenceStore(None)
        self.source_service = source_service

    def emit_speed_violation(
        self,
        *,
        frame_metadata,
        detection,
        frame,
        camera_id: str,
        speed_limit: float,
        radar_speed: float | None = None,
        save_evidence: bool = True,
    ) -> GeneratedEventRecord | None:
        estimated_speed = self._resolve_estimated_speed(detection)
        if estimated_speed is None or estimated_speed <= speed_limit:
            return None

        timestamp = self._resolve_timestamp(frame_metadata)
        event_id = str(uuid4())
        evidence_path = None
        if save_evidence:
            evidence_path = self.evidence_store.save_detection_evidence(
                frame=frame,
                camera_id=camera_id,
                track_id=detection.track_id,
                frame_index=frame_metadata.frame_index,
                timestamp_ms=frame_metadata.timestamp_ms,
                bounding_box=detection.bounding_box,
                estimated_speed=estimated_speed,
                radar_speed=radar_speed,
            )

        fused_speed = (
            round((estimated_speed + radar_speed) / 2.0, 2)
            if radar_speed is not None
            else round(estimated_speed, 2)
        )
        violation_amount = max(fused_speed - float(speed_limit), 0.0)
        payload = {
            "schema_version": "1.0.0",
            "event_type": "speed.violation_alert",
            "event_id": event_id,
            "source_service": self.source_service,
            "emitted_at": utc_now_iso(),
            "timestamp": timestamp,
            "camera_id": camera_id,
            "severity": self._resolve_severity(violation_amount),
            "matched": detection.track_id is not None,
            "confidence_score": round(float(detection.confidence), 4),
            "speed_limit": round(float(speed_limit), 2),
            "estimated_speed": round(float(estimated_speed), 2),
            "radar_speed": round(float(radar_speed), 2) if radar_speed is not None else None,
            "fused_speed": fused_speed,
            "violation_amount": round(violation_amount, 2),
            "track_id": detection.track_id,
            "label": detection.label,
            "radar": self._build_radar_payload(
                radar_speed=radar_speed,
                timestamp_ms=frame_metadata.timestamp_ms,
            ),
            "visual": {
                "track_id": detection.track_id,
                "label": detection.label,
                "speed": round(float(estimated_speed), 2),
                "confidence": round(float(detection.confidence), 4),
                "bounding_box": {
                    "x1": detection.bounding_box.x1,
                    "y1": detection.bounding_box.y1,
                    "x2": detection.bounding_box.x2,
                    "y2": detection.bounding_box.y2,
                },
            },
            "image_evidence_path": evidence_path,
            "metadata": {
                "frame_index": frame_metadata.frame_index,
                "frame_source": frame_metadata.source,
                "timestamp_ms": frame_metadata.timestamp_ms,
                "sampled_fps": frame_metadata.sampled_fps,
                "speed_estimation_method": (
                    detection.speed_estimate.method if detection.speed_estimate else None
                ),
                "speed_estimate_source": (
                    detection.speed_estimate.source if detection.speed_estimate else None
                ),
            },
        }

        delivery_result = self.publisher.publish(
            event_type="speed.violation_alert",
            camera_id=camera_id,
            occurred_at=timestamp,
            severity=payload["severity"],
            payload=payload,
        )

        return GeneratedEventRecord(
            event_type="speed.violation_alert",
            camera_id=camera_id,
            timestamp=timestamp,
            track_id=detection.track_id,
            estimated_speed=payload["estimated_speed"],
            radar_speed=payload["radar_speed"],
            confidence_score=payload["confidence_score"],
            image_evidence_path=evidence_path,
            delivery_status=delivery_result.get("delivery_status", "pending"),
            gateway_event_id=delivery_result.get("gateway_event_id"),
            gateway_status_code=delivery_result.get("gateway_status_code"),
            payload=payload,
        )

    @staticmethod
    def _resolve_estimated_speed(detection) -> float | None:
        if detection.speed_estimate is None:
            return None
        if detection.speed_estimate.corrected_speed_kmh is not None:
            return float(detection.speed_estimate.corrected_speed_kmh)
        if detection.speed_estimate.relative_speed_kmh is not None:
            return float(detection.speed_estimate.relative_speed_kmh)
        return None

    @staticmethod
    def _resolve_timestamp(frame_metadata) -> str:
        if frame_metadata.captured_at:
            return frame_metadata.captured_at
        return utc_now_iso()

    @staticmethod
    def _resolve_severity(violation_amount: float) -> str:
        if violation_amount >= 20.0:
            return "critical"
        return "warning"

    @staticmethod
    def _build_radar_payload(*, radar_speed: float | None, timestamp_ms: float | None):
        if radar_speed is None:
            return None
        return {
            "source": "pipeline-optional-radar",
            "reading_id": f"video-pipeline-{int(timestamp_ms or 0)}",
            "relative_speed": round(float(radar_speed), 2),
            "absolute_speed": round(float(radar_speed), 2),
            "patrol_speed": 0.0,
            "patrol_accel": 0.0,
            "signal_confidence": 0.5,
            "timestamp_ms": timestamp_ms,
        }
