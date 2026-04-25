"""Camera calibration module for speed estimation based on perspective and scale."""

from __future__ import annotations


class CameraCalibration:
    def __init__(
        self,
        pixels_per_meter: float = 20.0,
        camera_height_m: float = 5.0,
        camera_angle_deg: float = 30.0,
        lane_width_m: float = 3.5,
        reference_object_width_px: int | None = None,
        reference_object_width_m: float | None = None,
    ):
        # pixels_per_meter: kamera açısına göre yatay ölçek
        # Eğer reference_object verilmişse otomatik hesapla
        if reference_object_width_px and reference_object_width_m:
            self.pixels_per_meter = reference_object_width_px / reference_object_width_m
        else:
            self.pixels_per_meter = pixels_per_meter

    def pixels_to_meters(self, pixel_distance: float) -> float:
        return pixel_distance / self.pixels_per_meter

    def estimate_speed_kmh(
        self,
        pixel_distance: float,
        time_delta_seconds: float,
    ) -> float | None:
        if time_delta_seconds <= 0:
            return None
        meters = self.pixels_to_meters(pixel_distance)
        speed_ms = meters / time_delta_seconds
        return speed_ms * 3.6
