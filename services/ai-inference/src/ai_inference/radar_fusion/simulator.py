"""Deterministic simulated radar input for MVP fusion flows."""

from __future__ import annotations

from ..utils import RadarSpeedReading


class RadarSpeedSimulator:
    """Generate a simulated radar reading from tracked vehicle estimates."""

    def __init__(
        self,
        *,
        fallback_signal_confidence: float = 0.72,
        reading_scale: float = 0.98,
        min_relative_speed: float = 0.0,
    ):
        self.fallback_signal_confidence = float(fallback_signal_confidence)
        self.reading_scale = float(reading_scale)
        self.min_relative_speed = float(min_relative_speed)

    def simulate(
        self,
        *,
        vehicle_tracks,
        patrol_speed: float = 0.0,
        patrol_accel: float = 0.0,
        timestamp_ms: float | None = None,
    ) -> RadarSpeedReading:
        lead_track = self._select_lead_track(vehicle_tracks)
        estimated_speed = self._track_estimated_speed(lead_track) if lead_track is not None else 0.0
        radar_absolute_speed = max(estimated_speed * self.reading_scale, 0.0)
        relative_speed = max(radar_absolute_speed - patrol_speed, self.min_relative_speed)
        signal_confidence = (
            self._track_detection_confidence(lead_track)
            if lead_track is not None
            else self.fallback_signal_confidence
        )
        source = "simulated-radar"
        if lead_track and lead_track.get("label"):
            source = f"simulated-radar:{lead_track['label']}"

        return RadarSpeedReading(
            relative_speed=relative_speed,
            patrol_speed=patrol_speed,
            patrol_accel=patrol_accel,
            source=source,
            signal_confidence=signal_confidence,
            timestamp_ms=timestamp_ms,
        )

    def _select_lead_track(self, vehicle_tracks):
        best_track = None
        best_score = float("-inf")
        for track in vehicle_tracks.values():
            estimated_speed = self._track_estimated_speed(track)
            detection_confidence = self._track_detection_confidence(track)
            score = estimated_speed + (detection_confidence * 10.0)
            if score > best_score:
                best_score = score
                best_track = track
        return best_track

    @staticmethod
    def _track_estimated_speed(track) -> float:
        if not track:
            return 0.0
        speed_estimate = track.get("speed_estimate")
        if isinstance(speed_estimate, dict):
            speed_value = speed_estimate.get("corrected_speed_kmh")
            if speed_value is None:
                speed_value = speed_estimate.get("relative_speed_kmh")
            if speed_value is not None:
                return float(speed_value)
        if speed_estimate is not None and hasattr(speed_estimate, "corrected_speed_kmh"):
            speed_value = speed_estimate.corrected_speed_kmh
            if speed_value is None:
                speed_value = speed_estimate.relative_speed_kmh
            if speed_value is not None:
                return float(speed_value)
        if track.get("speed") is not None:
            return float(track["speed"])
        return 0.0

    @staticmethod
    def _track_detection_confidence(track) -> float:
        if not track:
            return 0.0
        raw_value = track.get("confidence", track.get("detection_confidence", 0.6))
        raw_value = float(raw_value)
        if raw_value < 0.0:
            return 0.0
        if raw_value > 1.0:
            return 1.0
        return raw_value
