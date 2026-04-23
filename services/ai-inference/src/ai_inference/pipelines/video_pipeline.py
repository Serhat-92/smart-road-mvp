"""Local-file video detection pipeline with modular source adapters."""

import math
import time

from ..tracker import ApproximateSpeedEstimator, SimpleMultiObjectTracker
from ..utils import FrameDetectionResult, FrameMetadata, VideoDetectionResult
from .video_sources import VideoSourceFactory


class VideoDetectionPipeline:
    """Read video frames, sample at a target FPS, and run detection."""

    def __init__(
        self,
        detector,
        source_factory=None,
        tracker_factory=None,
        speed_estimator_factory=None,
    ):
        self.detector = detector
        self.source_factory = source_factory or VideoSourceFactory()
        self.tracker_factory = tracker_factory or SimpleMultiObjectTracker
        self.speed_estimator_factory = speed_estimator_factory or ApproximateSpeedEstimator

    def run(
        self,
        source,
        sample_rate_fps=1.0,
        max_frames=None,
        use_tracking=False,
        speed_limit=None,
        camera_id=None,
        emit_speed_events=True,
        radar_speed=None,
        event_emitter=None,
        save_evidence=True,
    ) -> VideoDetectionResult:
        if sample_rate_fps <= 0:
            raise ValueError("sample_rate_fps must be greater than 0")

        frame_source = self.source_factory.create(source)
        frame_source.open()

        source_fps = self._normalize_fps(frame_source.fps)
        processed_frames = 0
        sampled_frames = 0
        current_frame_index = 0
        frame_results = []
        last_sample_wall_time = None
        sample_interval_seconds = 1.0 / sample_rate_fps
        sample_interval_frames = self._compute_frame_interval(
            source_fps=source_fps,
            sample_rate_fps=sample_rate_fps,
        )
        use_wall_clock_sampling = source_fps is None
        tracking_enabled = use_tracking or speed_limit is not None
        tracker = self.tracker_factory() if tracking_enabled else None
        speed_estimator = self.speed_estimator_factory() if tracking_enabled else None
        generated_events = []
        published_track_ids = set()

        try:
            while True:
                ok, frame = frame_source.read()
                if not ok:
                    break

                processed_frames += 1
                should_sample = self._should_sample_frame(
                    frame_index=current_frame_index,
                    sample_interval_frames=sample_interval_frames,
                    sample_interval_seconds=sample_interval_seconds,
                    last_sample_wall_time=last_sample_wall_time,
                    use_wall_clock_sampling=use_wall_clock_sampling,
                )

                if should_sample:
                    raw_result = self.detector.detect(frame)
                    detections = self.detector.to_structured_detections(raw_result)
                    if tracker is not None:
                        detections = tracker.update(detections)
                    if speed_estimator is not None:
                        detections = speed_estimator.update(
                            detections,
                            timestamp_s=self._resolve_timestamp_seconds(
                                timestamp_ms=frame_source.timestamp_ms,
                                frame_index=current_frame_index,
                                source_fps=source_fps,
                            ),
                        )
                    frame_metadata = self._build_frame_metadata(
                        frame=frame,
                        source=frame_source.source_name,
                        frame_index=current_frame_index,
                        timestamp_ms=frame_source.timestamp_ms,
                        source_fps=source_fps,
                        sampled_fps=sample_rate_fps,
                    )
                    frame_results.append(
                        FrameDetectionResult(
                            frame=frame_metadata,
                            detections=detections,
                        )
                    )
                    if (
                        event_emitter is not None
                        and emit_speed_events
                        and speed_limit is not None
                    ):
                        generated_events.extend(
                            self._emit_speed_violation_events(
                                frame=frame,
                                frame_metadata=frame_metadata,
                                detections=detections,
                                camera_id=camera_id or "camera-01",
                                speed_limit=speed_limit,
                                radar_speed=radar_speed,
                                event_emitter=event_emitter,
                                published_track_ids=published_track_ids,
                                save_evidence=save_evidence,
                            )
                        )
                    sampled_frames += 1
                    last_sample_wall_time = time.monotonic()

                current_frame_index += 1
                if max_frames is not None and processed_frames >= max_frames:
                    break
        finally:
            frame_source.release()

        return VideoDetectionResult(
            source=str(frame_source.source_name),
            sample_rate_fps=sample_rate_fps,
            processed_frames=processed_frames,
            sampled_frames=sampled_frames,
            source_fps=source_fps,
            frames=frame_results,
            generated_events=generated_events,
        )

    @staticmethod
    def _compute_frame_interval(source_fps, sample_rate_fps):
        if source_fps is None or sample_rate_fps >= source_fps:
            return 1
        return max(int(round(source_fps / sample_rate_fps)), 1)

    @staticmethod
    def _normalize_fps(raw_fps):
        if raw_fps is None:
            return None
        if not math.isfinite(raw_fps) or raw_fps <= 0:
            return None
        return float(raw_fps)

    @staticmethod
    def _should_sample_frame(
        frame_index,
        sample_interval_frames,
        sample_interval_seconds,
        last_sample_wall_time,
        use_wall_clock_sampling,
    ):
        if not use_wall_clock_sampling:
            return frame_index % sample_interval_frames == 0
        if last_sample_wall_time is None:
            return True
        return (time.monotonic() - last_sample_wall_time) >= sample_interval_seconds

    @staticmethod
    def _build_frame_metadata(frame, source, frame_index, timestamp_ms, source_fps, sampled_fps):
        height, width = frame.shape[:2]
        return FrameMetadata(
            source=str(source),
            frame_index=frame_index,
            timestamp_ms=float(timestamp_ms) if timestamp_ms is not None else None,
            source_fps=source_fps,
            width=int(width),
            height=int(height),
            sampled_fps=sampled_fps,
        )

    @staticmethod
    def _resolve_timestamp_seconds(timestamp_ms, frame_index, source_fps):
        if timestamp_ms is not None:
            return float(timestamp_ms) / 1000.0
        if source_fps is not None and source_fps > 0:
            return float(frame_index) / float(source_fps)
        return time.monotonic()

    @staticmethod
    def _emit_speed_violation_events(
        *,
        frame,
        frame_metadata,
        detections,
        camera_id,
        speed_limit,
        radar_speed,
        event_emitter,
        published_track_ids,
        save_evidence,
    ):
        generated_events = []
        for detection in detections:
            if detection.track_id is None or detection.track_id in published_track_ids:
                continue

            event_record = event_emitter.emit_speed_violation(
                frame_metadata=frame_metadata,
                detection=detection,
                frame=frame,
                camera_id=camera_id,
                speed_limit=speed_limit,
                radar_speed=radar_speed,
                save_evidence=save_evidence,
            )
            if event_record is None:
                continue

            published_track_ids.add(detection.track_id)
            generated_events.append(event_record)
        return generated_events
