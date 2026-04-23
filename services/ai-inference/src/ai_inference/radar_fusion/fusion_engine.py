"""Sensor fusion logic for radar and visual detections."""

from ..utils import FusionMetadata


class RadarFusionEngine:
    def __init__(self, unstable_accel_threshold=2.0, min_radar_speed=5.0, verify_diff=25.0):
        self.unstable_accel_threshold = unstable_accel_threshold
        self.min_radar_speed = min_radar_speed
        self.verify_diff = verify_diff

    def apply(self, vehicle_data, radar_relative_speed, patrol_speed, patrol_accel):
        metadata = FusionMetadata(
            radar_relative_speed=radar_relative_speed,
            patrol_speed=patrol_speed,
            patrol_accel=patrol_accel,
            is_stable=abs(patrol_accel) < self.unstable_accel_threshold,
        )

        if radar_relative_speed is None:
            return vehicle_data, metadata

        metadata.radar_absolute_speed = radar_relative_speed + patrol_speed

        if not vehicle_data:
            return vehicle_data, metadata

        if radar_relative_speed > self.min_radar_speed and metadata.is_stable:
            best_match_id = None
            min_diff = float("inf")

            for vehicle_id, vehicle_state in vehicle_data.items():
                visual_val = vehicle_state["speed"]
                diff = abs(visual_val - metadata.radar_absolute_speed)
                if diff < min_diff:
                    min_diff = diff
                    best_match_id = vehicle_id

            metadata.matched_track_id = best_match_id
            metadata.match_difference = min_diff if min_diff != float("inf") else None

            if best_match_id is not None:
                car_data = vehicle_data[best_match_id]
                car_data["radar_speed"] = metadata.radar_absolute_speed

                if min_diff < self.verify_diff:
                    car_data["fusion_status"] = "VERIFIED"
                    car_data["color"] = (0, 255, 0)
                else:
                    car_data["fusion_status"] = "UNCERTAIN"
                    car_data["color"] = (0, 255, 255)

                car_data["speed"] = metadata.radar_absolute_speed

        elif not metadata.is_stable:
            for vehicle_id in vehicle_data:
                vehicle_data[vehicle_id]["fusion_status"] = "UNSTABLE"
                vehicle_data[vehicle_id]["radar_speed"] = 0
        else:
            for vehicle_id in vehicle_data:
                vehicle_data[vehicle_id]["radar_speed"] = 0
                vehicle_data[vehicle_id]["fusion_status"] = None

        return vehicle_data, metadata
