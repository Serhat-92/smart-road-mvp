# AI Inference Service

This service owns the radar-side runtime:

- YOLO vehicle detection and tracking
- visual speed estimation
- radar and patrol-speed sensor fusion
- evidence packaging and optional HQ upload

## Structure

- `src/ai_inference/detector/`: detector implementations, including `yolo_detector.py`
- `src/ai_inference/tracker/`: speed and motion tracking logic
- `src/ai_inference/radar_fusion/`: visual plus radar fusion rules
- `src/ai_inference/pipelines/`: frame orchestration pipeline
- `src/ai_inference/utils/`: shared inference result types
- `src/ai_inference/api.py`: simple `infer_frame(...)` facade
- `src/ai_inference/pipelines/video_pipeline.py`: video or RTSP sampling pipeline
- `src/ai_inference/radar_fusion/event_fusion.py`: confidence-based radar event matcher

## Simple API

```python
from ai_inference import AIInferenceService

service = AIInferenceService(speed_factor=36.0)
result = service.infer_frame(frame, radar_relative_speed=65, patrol_speed=70)
print(result.track_count)
```

## Video Pipeline

```python
from ai_inference import AIInferenceService

service = AIInferenceService()
result = service.infer_video("video.mp4", sample_rate_fps=2.0)

for frame_result in result.frames:
    print(frame_result.frame.frame_index, len(frame_result.detections))
```

Each sampled frame returns structured detections with:

- bounding boxes
- labels
- confidence scores
- frame metadata such as index, timestamp, source FPS, and frame size
- optional `speed_estimate` data when tracking is enabled

## Approximate Speed Estimation

When `use_tracking=true`, the service keeps lightweight track IDs across frames and
computes an approximate computer-vision-based relative speed estimate in km/h.

- The estimate is based on tracked object movement in image space.
- A configurable calibration factor converts normalized motion into km/h.
- The output is explicitly marked as approximate and uncorrected so radar-based
  correction can be added later without changing the response shape.

## HTTP Service

Run locally:

```bash
python services/ai-inference/service_api.py
```

Available endpoints:

- `GET /health`
- `POST /frame/analyze`
  Accepts `multipart/form-data` with an image file and returns structured detections for a single frame.
- `POST /frame/analyze/base64`
  Accepts a base64-encoded frame payload for service-to-service requests.
- `POST /video/analyze`
  Reads a local video file or RTSP source and returns sampled frame detections.
- `POST /radar/fuse`
  Matches radar speed readings with visual tracks.

## Radar Event Fusion

```python
from ai_inference import AIInferenceService

service = AIInferenceService()
event = service.fuse_radar_event(
    vehicle_tracks={
        12: {"speed": 108.0, "box": [10, 20, 110, 150], "label": "car", "confidence": 0.92}
    },
    radar_speed_data={"relative_speed": 42.0, "patrol_speed": 70.0, "signal_confidence": 0.9},
    speed_limit=90,
)

print(event.to_payload())
```

The matcher chooses the best visual track using a simple confidence score based on:

- radar and visual speed alignment
- detector confidence, when available
- radar signal confidence
