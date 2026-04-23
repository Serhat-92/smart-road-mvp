"""Lightweight multi-object tracker for MVP inference flows."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math

from ..utils import BoundingBox, DetectionRecord


@dataclass
class _TrackState:
    track_id: int
    label: str
    class_id: int | None
    bounding_box: BoundingBox
    missed_frames: int = 0


class SimpleMultiObjectTracker:
    """Assigns stable track IDs using IoU plus centroid distance matching."""

    def __init__(
        self,
        *,
        min_iou: float = 0.1,
        max_center_distance: float = 120.0,
        max_missed_frames: int = 4,
    ):
        self.min_iou = float(min_iou)
        self.max_center_distance = float(max_center_distance)
        self.max_missed_frames = int(max_missed_frames)
        self._next_track_id = 1
        self._tracks: dict[int, _TrackState] = {}

    def reset(self) -> None:
        self._next_track_id = 1
        self._tracks.clear()

    def update(self, detections: list[DetectionRecord]) -> list[DetectionRecord]:
        if not detections:
            self._age_unmatched_tracks(matched_track_ids=set())
            return []

        track_ids = list(self._tracks.keys())
        candidates = []
        for track_id in track_ids:
            track = self._tracks[track_id]
            for detection_index, detection in enumerate(detections):
                if not self._is_compatible(track, detection):
                    continue

                score = self._match_score(track.bounding_box, detection.bounding_box)
                if score <= 0:
                    continue
                candidates.append((score, track_id, detection_index))

        candidates.sort(reverse=True, key=lambda item: item[0])

        matched_track_ids = set()
        matched_detection_indices = set()
        tracked_detections: list[DetectionRecord] = [None] * len(detections)  # type: ignore[list-item]

        for score, track_id, detection_index in candidates:
            if track_id in matched_track_ids or detection_index in matched_detection_indices:
                continue

            matched_track_ids.add(track_id)
            matched_detection_indices.add(detection_index)
            detection = detections[detection_index]
            self._tracks[track_id] = _TrackState(
                track_id=track_id,
                label=detection.label,
                class_id=detection.class_id,
                bounding_box=detection.bounding_box,
                missed_frames=0,
            )
            tracked_detections[detection_index] = replace(detection, track_id=track_id)

        for detection_index, detection in enumerate(detections):
            if detection_index in matched_detection_indices:
                continue

            track_id = self._next_track_id
            self._next_track_id += 1
            self._tracks[track_id] = _TrackState(
                track_id=track_id,
                label=detection.label,
                class_id=detection.class_id,
                bounding_box=detection.bounding_box,
                missed_frames=0,
            )
            tracked_detections[detection_index] = replace(detection, track_id=track_id)

        self._age_unmatched_tracks(matched_track_ids=matched_track_ids)
        return tracked_detections

    def _age_unmatched_tracks(self, matched_track_ids: set[int]) -> None:
        stale_track_ids = []
        for track_id, track in self._tracks.items():
            if track_id in matched_track_ids:
                continue
            track.missed_frames += 1
            if track.missed_frames > self.max_missed_frames:
                stale_track_ids.append(track_id)

        for track_id in stale_track_ids:
            del self._tracks[track_id]

    def _is_compatible(self, track: _TrackState, detection: DetectionRecord) -> bool:
        if track.class_id is not None and detection.class_id is not None:
            return track.class_id == detection.class_id
        return track.label == detection.label

    def _match_score(self, track_box: BoundingBox, detection_box: BoundingBox) -> float:
        iou = self._intersection_over_union(track_box, detection_box)
        if iou >= self.min_iou:
            return iou + 1.0

        distance = self._center_distance(track_box, detection_box)
        if distance > self.max_center_distance:
            return 0.0

        distance_score = 1.0 - (distance / max(self.max_center_distance, 1.0))
        return max(distance_score, 0.0)

    @staticmethod
    def _intersection_over_union(box_a: BoundingBox, box_b: BoundingBox) -> float:
        x_left = max(box_a.x1, box_b.x1)
        y_top = max(box_a.y1, box_b.y1)
        x_right = min(box_a.x2, box_b.x2)
        y_bottom = min(box_a.y2, box_b.y2)

        intersection_width = max(0.0, x_right - x_left)
        intersection_height = max(0.0, y_bottom - y_top)
        intersection_area = intersection_width * intersection_height
        if intersection_area <= 0:
            return 0.0

        area_a = max(0.0, box_a.x2 - box_a.x1) * max(0.0, box_a.y2 - box_a.y1)
        area_b = max(0.0, box_b.x2 - box_b.x1) * max(0.0, box_b.y2 - box_b.y1)
        union_area = area_a + area_b - intersection_area
        if union_area <= 0:
            return 0.0
        return intersection_area / union_area

    @staticmethod
    def _center_distance(box_a: BoundingBox, box_b: BoundingBox) -> float:
        center_a = ((box_a.x1 + box_a.x2) / 2.0, (box_a.y1 + box_a.y2) / 2.0)
        center_b = ((box_b.x1 + box_b.x2) / 2.0, (box_b.y1 + box_b.y2) / 2.0)
        return math.dist(center_a, center_b)
