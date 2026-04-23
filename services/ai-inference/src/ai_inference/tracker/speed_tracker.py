"""Approximate computer-vision speed estimation for tracked vehicles."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
import statistics
import time

from ..utils import BoundingBox, DetectionRecord, SpeedEstimate


@dataclass
class _SpeedTrackState:
    history: list[tuple[float, tuple[float, float], float]]
    speed_buffer: list[float]
    last_speed_kmh: float
    missed_frames: int = 0


class ApproximateSpeedEstimator:
    """Estimate relative vehicle speed from tracked motion across frames.

    This estimator is intentionally approximate. It converts normalized image-space
    motion into km/h using a configurable calibration factor. The output is marked
    as a computer-vision estimate so radar-based correction can be layered on later.
    """

    def __init__(
        self,
        calibration_factor: float = 36.0,
        *,
        history_size: int = 6,
        smoothing_window: int = 5,
        max_missed_frames: int = 4,
        max_reasonable_speed_kmh: float = 300.0,
    ):
        self.calibration_factor = float(calibration_factor)
        self.history_size = int(history_size)
        self.smoothing_window = int(smoothing_window)
        self.max_missed_frames = int(max_missed_frames)
        self.max_reasonable_speed_kmh = float(max_reasonable_speed_kmh)
        self._track_states: dict[int, _SpeedTrackState] = {}

    def reset(self) -> None:
        self._track_states.clear()

    def update(
        self,
        detections: list[DetectionRecord],
        *,
        timestamp_s: float | None = None,
    ) -> list[DetectionRecord]:
        timestamp_s = float(timestamp_s) if timestamp_s is not None else time.time()
        active_track_ids = set()
        updated_detections = []

        for detection in detections:
            if detection.track_id is None:
                updated_detections.append(detection)
                continue

            active_track_ids.add(detection.track_id)
            state = self._track_states.setdefault(
                detection.track_id,
                _SpeedTrackState(
                    history=[],
                    speed_buffer=[],
                    last_speed_kmh=0.0,
                ),
            )

            centroid = self._centroid(detection.bounding_box)
            box_height = max(detection.bounding_box.y2 - detection.bounding_box.y1, 1.0)
            state.history.append((timestamp_s, centroid, box_height))
            if len(state.history) > self.history_size:
                state.history.pop(0)

            estimated_speed_kmh = self._estimate_speed_kmh(state)
            if estimated_speed_kmh is not None:
                state.speed_buffer.append(estimated_speed_kmh)
                if len(state.speed_buffer) > self.smoothing_window:
                    state.speed_buffer.pop(0)
                estimated_speed_kmh = statistics.median(state.speed_buffer)
                state.last_speed_kmh = estimated_speed_kmh
            elif state.last_speed_kmh > 0:
                estimated_speed_kmh = state.last_speed_kmh

            state.missed_frames = 0
            updated_detections.append(
                replace(
                    detection,
                    speed_estimate=SpeedEstimate(
                        relative_speed_kmh=estimated_speed_kmh,
                        calibration_factor=self.calibration_factor,
                    ),
                )
            )

        self._age_tracks(active_track_ids)
        return updated_detections

    def _estimate_speed_kmh(self, state: _SpeedTrackState) -> float | None:
        if len(state.history) < 2:
            return None

        first_timestamp, first_centroid, first_height = state.history[0]
        last_timestamp, last_centroid, last_height = state.history[-1]
        delta_time = last_timestamp - first_timestamp
        if delta_time <= 0:
            return None

        pixel_distance = math.dist(first_centroid, last_centroid)
        reference_height = max((first_height + last_height) / 2.0, 1.0)
        normalized_motion = pixel_distance / reference_height
        relative_speed_kmh = (normalized_motion / delta_time) * self.calibration_factor

        if pixel_distance < 0.5:
            return 0.0
        if relative_speed_kmh > self.max_reasonable_speed_kmh:
            return state.last_speed_kmh if state.last_speed_kmh > 0 else None
        return relative_speed_kmh

    def _age_tracks(self, active_track_ids: set[int]) -> None:
        stale_track_ids = []
        for track_id, state in self._track_states.items():
            if track_id in active_track_ids:
                continue
            state.missed_frames += 1
            if state.missed_frames > self.max_missed_frames:
                stale_track_ids.append(track_id)

        for track_id in stale_track_ids:
            del self._track_states[track_id]

    @staticmethod
    def _centroid(box: BoundingBox) -> tuple[float, float]:
        return ((box.x1 + box.x2) / 2.0, (box.y1 + box.y2) / 2.0)


class SpeedEstimator:
    """Backward-compatible wrapper used by the radar-oriented frame pipeline."""

    def __init__(self, speed_factor=36.0):
        self.approximate_estimator = ApproximateSpeedEstimator(
            calibration_factor=speed_factor
        )
        self.captured_track_ids: set[int] = set()

    def update(self, detections):
        current_time = time.time()
        current_data = {}

        boxes = getattr(detections, "boxes", None)
        if boxes is None or boxes.id is None:
            return current_data

        ids = boxes.id.int().cpu().tolist()
        coordinates = boxes.xyxy.cpu().tolist()
        class_ids = boxes.cls.int().cpu().tolist() if boxes.cls is not None else []
        confidences = boxes.conf.cpu().tolist() if boxes.conf is not None else []
        names = getattr(detections, "names", {})

        structured_detections = []
        for index, track_id in enumerate(ids):
            class_id = class_ids[index] if index < len(class_ids) else None
            confidence = confidences[index] if index < len(confidences) else 0.0
            label = self._resolve_label(names, class_id)
            box = coordinates[index]
            structured_detections.append(
                DetectionRecord(
                    label=label,
                    confidence=float(confidence),
                    bounding_box=BoundingBox(
                        x1=float(box[0]),
                        y1=float(box[1]),
                        x2=float(box[2]),
                        y2=float(box[3]),
                    ),
                    class_id=class_id,
                    track_id=track_id,
                )
            )

        tracked_detections = self.approximate_estimator.update(
            structured_detections,
            timestamp_s=current_time,
        )
        for detection in tracked_detections:
            current_data[detection.track_id] = {
                "box": [
                    detection.bounding_box.x1,
                    detection.bounding_box.y1,
                    detection.bounding_box.x2,
                    detection.bounding_box.y2,
                ],
                "speed": detection.speed_estimate.relative_speed_kmh
                if detection.speed_estimate and detection.speed_estimate.relative_speed_kmh is not None
                else 0.0,
                "speed_estimate": detection.speed_estimate,
                "captured": detection.track_id in self.captured_track_ids,
            }

        return current_data

    def mark_captured(self, track_id):
        self.captured_track_ids.add(track_id)

    @staticmethod
    def _resolve_label(names, class_id):
        if class_id is None:
            return "unknown"
        if isinstance(names, dict):
            return str(names.get(class_id, class_id))
        if isinstance(names, (list, tuple)) and 0 <= class_id < len(names):
            return str(names[class_id])
        return str(class_id)
