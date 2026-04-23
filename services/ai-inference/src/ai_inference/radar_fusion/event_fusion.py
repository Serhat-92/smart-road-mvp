"""Confidence-based radar-to-track event fusion for MVP use."""

from __future__ import annotations

from ..utils import BoundingBox, FusedViolationEvent, RadarSpeedReading, RadarTrackMatch
from .simulator import RadarSpeedSimulator


class RadarEventFusion:
    """Match radar readings to tracked vehicles and emit fused speed events."""

    def __init__(
        self,
        max_speed_delta=35.0,
        min_match_confidence=0.45,
        min_violation_confidence=0.55,
        unstable_accel_threshold=2.0,
        min_relative_speed=5.0,
        alignment_weight=0.6,
        detection_weight=0.25,
        signal_weight=0.15,
        simulator=None,
    ):
        self.max_speed_delta = max_speed_delta
        self.min_match_confidence = min_match_confidence
        self.min_violation_confidence = min_violation_confidence
        self.unstable_accel_threshold = unstable_accel_threshold
        self.min_relative_speed = min_relative_speed
        self.alignment_weight = alignment_weight
        self.detection_weight = detection_weight
        self.signal_weight = signal_weight
        self.simulator = simulator or RadarSpeedSimulator()

    def fuse_speed_violation_event(
        self,
        radar_reading=None,
        vehicle_tracks=None,
        speed_limit=0.0,
        patrol_speed=0.0,
        patrol_accel=0.0,
    ) -> FusedViolationEvent:
        vehicle_tracks = vehicle_tracks or {}
        reading, radar_mode = self._resolve_reading(
            radar_reading=radar_reading,
            vehicle_tracks=vehicle_tracks,
            patrol_speed=patrol_speed,
            patrol_accel=patrol_accel,
        )

        if reading.relative_speed < self.min_relative_speed:
            return self._unmatched_event(
                reading=reading,
                speed_limit=speed_limit,
                fusion_status="RADAR_TOO_LOW",
                radar_mode=radar_mode,
                vehicle_track_count=len(vehicle_tracks),
            )

        if abs(reading.patrol_accel) >= self.unstable_accel_threshold:
            return self._unmatched_event(
                reading=reading,
                speed_limit=speed_limit,
                fusion_status="UNSTABLE",
                radar_mode=radar_mode,
                vehicle_track_count=len(vehicle_tracks),
            )

        match = self.match_tracks(reading=reading, vehicle_tracks=vehicle_tracks)
        estimated_speed = match.visual_speed
        fused_speed = None
        violation_amount = None
        is_violation = False

        if match.matched and estimated_speed is not None:
            fused_speed = self._compute_fused_speed(
                radar_speed=match.radar_speed,
                estimated_speed=estimated_speed,
                confidence_score=match.confidence_score,
            )
            if (
                fused_speed > speed_limit
                and match.confidence_score >= self.min_violation_confidence
            ):
                is_violation = True
                violation_amount = fused_speed - speed_limit

        event_type = self._resolve_event_type(
            matched=match.matched,
            is_violation=is_violation,
            fused_speed=fused_speed,
            speed_limit=speed_limit,
        )

        return FusedViolationEvent(
            event_type=event_type,
            source=reading.source,
            matched=match.matched,
            is_potential_violation=is_violation,
            confidence_score=round(match.confidence_score, 4),
            speed_limit=speed_limit,
            fused_speed=round(fused_speed, 2) if fused_speed is not None else None,
            estimated_speed=round(estimated_speed, 2) if estimated_speed is not None else None,
            violation_amount=round(violation_amount, 2)
            if violation_amount is not None
            else None,
            radar_speed=round(reading.absolute_speed, 2),
            radar_relative_speed=round(reading.relative_speed, 2),
            visual_speed=round(estimated_speed, 2) if estimated_speed is not None else None,
            speed_delta=round(match.speed_delta, 2) if match.speed_delta is not None else None,
            track_id=match.track_id,
            label=match.label,
            bounding_box=match.bounding_box,
            fusion_status=match.fusion_status,
            metadata={
                "reading_id": reading.reading_id,
                "timestamp_ms": reading.timestamp_ms,
                "patrol_speed": reading.patrol_speed,
                "patrol_accel": reading.patrol_accel,
                "signal_confidence": reading.signal_confidence,
                "vehicle_track_count": len(vehicle_tracks),
                "radar_mode": radar_mode,
            },
        )

    def match_tracks(self, reading: RadarSpeedReading, vehicle_tracks) -> RadarTrackMatch:
        best_match = None
        best_score = -1.0
        best_delta = None

        for track_id, track in vehicle_tracks.items():
            estimated_speed = self._track_estimated_speed(track)
            speed_delta = abs(estimated_speed - reading.absolute_speed)
            alignment_score = self._clamp(1.0 - (speed_delta / self.max_speed_delta))
            detection_confidence = self._track_detection_confidence(track)
            signal_confidence = self._clamp(reading.signal_confidence)
            score = (
                alignment_score * self.alignment_weight
                + detection_confidence * self.detection_weight
                + signal_confidence * self.signal_weight
            )

            if score > best_score:
                best_score = score
                best_delta = speed_delta
                best_match = RadarTrackMatch(
                    matched=score >= self.min_match_confidence,
                    track_id=track_id,
                    confidence_score=score,
                    radar_speed=reading.absolute_speed,
                    visual_speed=estimated_speed,
                    speed_delta=speed_delta,
                    label=track.get("label"),
                    bounding_box=self._coerce_bounding_box(track.get("box")),
                    detection_confidence=detection_confidence,
                    fusion_status=(
                        "MATCHED" if score >= self.min_match_confidence else "LOW_CONFIDENCE"
                    ),
                )

        if best_match is None:
            return RadarTrackMatch(
                matched=False,
                track_id=None,
                confidence_score=0.0,
                radar_speed=reading.absolute_speed,
                fusion_status="NO_TRACKS",
            )

        best_match.speed_delta = best_delta
        return best_match

    def _resolve_reading(
        self,
        *,
        radar_reading,
        vehicle_tracks,
        patrol_speed,
        patrol_accel,
    ):
        if radar_reading is not None:
            return self._coerce_reading(radar_reading), "hardware"

        simulated_reading = self.simulator.simulate(
            vehicle_tracks=vehicle_tracks,
            patrol_speed=patrol_speed,
            patrol_accel=patrol_accel,
        )
        return simulated_reading, "simulated"

    def _unmatched_event(
        self,
        *,
        reading: RadarSpeedReading,
        speed_limit: float,
        fusion_status: str,
        radar_mode: str,
        vehicle_track_count: int,
    ):
        return FusedViolationEvent(
            event_type="speed_observation",
            source=reading.source,
            matched=False,
            is_potential_violation=False,
            confidence_score=0.0,
            speed_limit=speed_limit,
            radar_speed=round(reading.absolute_speed, 2),
            radar_relative_speed=round(reading.relative_speed, 2),
            fusion_status=fusion_status,
            metadata={
                "reading_id": reading.reading_id,
                "timestamp_ms": reading.timestamp_ms,
                "patrol_speed": reading.patrol_speed,
                "patrol_accel": reading.patrol_accel,
                "signal_confidence": reading.signal_confidence,
                "radar_mode": radar_mode,
                "vehicle_track_count": vehicle_track_count,
            },
        )

    @staticmethod
    def _resolve_event_type(*, matched: bool, is_violation: bool, fused_speed, speed_limit: float):
        if not matched:
            return "speed_observation"
        if is_violation:
            return "speed_violation"
        if fused_speed is not None and fused_speed > speed_limit:
            return "speed_warning"
        return "speed_observation"

    @staticmethod
    def _track_detection_confidence(track):
        raw_value = track.get("confidence", track.get("detection_confidence", 0.6))
        return RadarEventFusion._clamp(raw_value)

    @staticmethod
    def _track_estimated_speed(track):
        speed_estimate = track.get("speed_estimate")
        if isinstance(speed_estimate, dict):
            corrected = speed_estimate.get("corrected_speed_kmh")
            if corrected is not None:
                return float(corrected)
            relative = speed_estimate.get("relative_speed_kmh")
            if relative is not None:
                return float(relative)
        if speed_estimate is not None and hasattr(speed_estimate, "corrected_speed_kmh"):
            corrected = speed_estimate.corrected_speed_kmh
            if corrected is not None:
                return float(corrected)
            relative = speed_estimate.relative_speed_kmh
            if relative is not None:
                return float(relative)

        if track.get("speed") is not None:
            return float(track["speed"])
        return 0.0

    @staticmethod
    def _compute_fused_speed(radar_speed, estimated_speed, confidence_score):
        radar_weight = 0.65 + (0.2 * RadarEventFusion._clamp(confidence_score))
        estimated_weight = 1.0 - radar_weight
        return (radar_speed * radar_weight) + (estimated_speed * estimated_weight)

    @staticmethod
    def _coerce_reading(radar_reading):
        if isinstance(radar_reading, RadarSpeedReading):
            return radar_reading
        return RadarSpeedReading(**radar_reading)

    @staticmethod
    def _coerce_bounding_box(raw_box):
        if raw_box is None:
            return None
        if isinstance(raw_box, BoundingBox):
            return raw_box
        if isinstance(raw_box, (list, tuple)) and len(raw_box) == 4:
            return BoundingBox(
                x1=float(raw_box[0]),
                y1=float(raw_box[1]),
                x2=float(raw_box[2]),
                y2=float(raw_box[3]),
            )
        return None

    @staticmethod
    def _clamp(value):
        value = float(value)
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return value
