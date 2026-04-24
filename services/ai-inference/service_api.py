"""HTTP service wrapper for ai-inference container and local deployments."""

from __future__ import annotations

from base64 import b64decode
from dataclasses import dataclass
from functools import lru_cache
import json
import logging
import os
import sys
from typing import Any

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.ai_inference import (
    AIInferenceService,
    EvidenceStore,
    FrameDetectionResult,
    GatewayEventPublisher,
    RadarEventFusion,
    RadarSpeedReading,
    SpeedViolationEventEmitter,
    VideoDetectionResult,
)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("path", "method", "status_code", "duration_ms", "model_path"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, default=str)


def configure_logging(level: str = "INFO") -> None:
    root_logger = logging.getLogger()
    if getattr(root_logger, "_ai_inference_logging_configured", False):
        root_logger.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
    root_logger._ai_inference_logging_configured = True  # type: ignore[attr-defined]


logger = logging.getLogger("ai_inference.service")


@dataclass(frozen=True)
class InferenceServiceSettings:
    host: str
    port: int
    environment: str
    model_path: str
    speed_factor: float
    lazy_model_load: bool
    log_level: str
    gateway_api_url: str | None
    gateway_timeout_s: float
    evidence_dir: str | None
    default_camera_id: str


@lru_cache
def get_settings() -> InferenceServiceSettings:
    return InferenceServiceSettings(
        host=os.getenv("AI_INFERENCE_HOST", "0.0.0.0"),
        port=int(os.getenv("AI_INFERENCE_PORT", "8090")),
        environment=os.getenv("AI_INFERENCE_ENV", "development"),
        model_path=os.getenv("AI_INFERENCE_MODEL_PATH", "yolov8n.pt"),
        speed_factor=float(os.getenv("AI_INFERENCE_SPEED_FACTOR", "36.0")),
        lazy_model_load=_as_bool(os.getenv("AI_INFERENCE_LAZY_MODEL"), default=True),
        log_level=os.getenv("AI_INFERENCE_LOG_LEVEL", "INFO").upper(),
        gateway_api_url=os.getenv("AI_INFERENCE_GATEWAY_API_URL", "http://127.0.0.1:8080"),
        gateway_timeout_s=float(os.getenv("AI_INFERENCE_GATEWAY_TIMEOUT_S", "5.0")),
        evidence_dir=os.getenv("AI_INFERENCE_EVIDENCE_DIR", "datasets/evidence"),
        default_camera_id=os.getenv("AI_INFERENCE_DEFAULT_CAMERA_ID", "camera-01"),
    )


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class BoundingBoxResponse(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class SpeedEstimateResponse(BaseModel):
    relative_speed_kmh: float | None = None
    source: str
    method: str
    is_approximate: bool
    calibration_factor: float | None = None
    correction_status: str
    corrected_speed_kmh: float | None = None


class DetectionResponse(BaseModel):
    label: str
    confidence: float
    bounding_box: BoundingBoxResponse
    class_id: int | None = None
    track_id: int | None = None
    speed_estimate: SpeedEstimateResponse | None = None


class FrameMetadataResponse(BaseModel):
    source: str
    frame_index: int
    captured_at: str | None = None
    timestamp_ms: float | None = None
    source_fps: float | None = None
    width: int | None = None
    height: int | None = None
    sampled_fps: float | None = None


class FrameAnalysisResponse(BaseModel):
    frame: FrameMetadataResponse
    detections: list[DetectionResponse]
    detection_count: int


class VideoAnalysisResponse(BaseModel):
    source: str
    sample_rate_fps: float
    processed_frames: int
    sampled_frames: int
    source_fps: float | None = None
    total_detections: int
    frames: list[FrameAnalysisResponse]
    generated_event_count: int
    generated_events: list["GeneratedEventResponse"] = Field(default_factory=list)


class GeneratedEventResponse(BaseModel):
    event_type: str
    camera_id: str
    timestamp: str
    track_id: int | None = None
    estimated_speed: float | None = None
    radar_speed: float | None = None
    confidence_score: float
    image_evidence_path: str | None = None
    delivery_status: str
    gateway_event_id: str | None = None
    gateway_status_code: int | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    lazy_model_load: bool
    model_loaded: bool
    model_path: str


class RadarTrackInput(BaseModel):
    speed: float = Field(..., ge=0.0)
    box: list[float] | None = Field(default=None, min_length=4, max_length=4)
    label: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class RadarFuseRequest(BaseModel):
    vehicle_tracks: dict[int, RadarTrackInput]
    radar_speed_data: dict | None = None
    speed_limit: float = Field(..., ge=0.0)
    patrol_speed: float = Field(default=0.0, ge=0.0)
    patrol_accel: float = 0.0


class VideoAnalyzeRequest(BaseModel):
    source: str
    sample_rate_fps: float = Field(default=1.0, gt=0.0)
    max_frames: int | None = Field(default=None, ge=1)
    use_tracking: bool = False
    camera_id: str | None = Field(default=None, min_length=1, max_length=120)
    speed_limit: float | None = Field(default=None, ge=0.0)
    emit_speed_events: bool = True
    radar_speed: float | None = Field(default=None, ge=0.0)
    save_evidence: bool = True


class Base64FrameAnalyzeRequest(BaseModel):
    frame_base64: str = Field(..., min_length=1)
    source: str = Field(default="image-frame")
    frame_index: int = Field(default=0, ge=0)
    timestamp_ms: float | None = None
    source_fps: float | None = Field(default=None, gt=0.0)
    sampled_fps: float | None = Field(default=None, gt=0.0)
    captured_at: str | None = None
    use_tracking: bool = False


if hasattr(VideoAnalysisResponse, "model_rebuild"):
    VideoAnalysisResponse.model_rebuild()
else:  # pragma: no cover - Pydantic v1
    VideoAnalysisResponse.update_forward_refs(GeneratedEventResponse=GeneratedEventResponse)


class InferenceAppState:
    def __init__(
        self,
        settings: InferenceServiceSettings,
        service_factory=AIInferenceService,
    ):
        from ai_inference.ocr import PlateReader

        self.settings = settings
        self.radar_fusion = RadarEventFusion()
        self.event_emitter = SpeedViolationEventEmitter(
            publisher=GatewayEventPublisher(
                base_url=settings.gateway_api_url,
                timeout_s=settings.gateway_timeout_s,
            ),
            evidence_store=EvidenceStore(settings.evidence_dir),
            plate_reader=PlateReader(),
        )
        self._service = None
        self._service_factory = service_factory

    @property
    def model_loaded(self) -> bool:
        return self._service is not None

    def get_service(self) -> AIInferenceService:
        if self._service is None:
            try:
                self._service = self._service_factory(
                    model_path=self.settings.model_path,
                    speed_factor=self.settings.speed_factor,
                )
            except Exception as exc:  # pragma: no cover - runtime dependency failure
                logger.exception(
                    "Failed to initialize AI inference service",
                    extra={"model_path": self.settings.model_path},
                )
                raise RuntimeError(
                    f"Unable to initialize AI inference model from {self.settings.model_path}"
                ) from exc
        return self._service


def model_to_dict(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def serialize_frame_result(result: FrameDetectionResult) -> FrameAnalysisResponse:
    return FrameAnalysisResponse(
        frame=FrameMetadataResponse(
            source=result.frame.source,
            frame_index=result.frame.frame_index,
            captured_at=result.frame.captured_at,
            timestamp_ms=result.frame.timestamp_ms,
            source_fps=result.frame.source_fps,
            width=result.frame.width,
            height=result.frame.height,
            sampled_fps=result.frame.sampled_fps,
        ),
        detections=[
            DetectionResponse(
                label=detection.label,
                confidence=detection.confidence,
                bounding_box=BoundingBoxResponse(
                    x1=detection.bounding_box.x1,
                    y1=detection.bounding_box.y1,
                    x2=detection.bounding_box.x2,
                    y2=detection.bounding_box.y2,
                ),
                class_id=detection.class_id,
                track_id=detection.track_id,
                speed_estimate=(
                    SpeedEstimateResponse(
                        relative_speed_kmh=detection.speed_estimate.relative_speed_kmh,
                        source=detection.speed_estimate.source,
                        method=detection.speed_estimate.method,
                        is_approximate=detection.speed_estimate.is_approximate,
                        calibration_factor=detection.speed_estimate.calibration_factor,
                        correction_status=detection.speed_estimate.correction_status,
                        corrected_speed_kmh=detection.speed_estimate.corrected_speed_kmh,
                    )
                    if detection.speed_estimate is not None
                    else None
                ),
            )
            for detection in result.detections
        ],
        detection_count=len(result.detections),
    )


def serialize_video_result(result: VideoDetectionResult) -> VideoAnalysisResponse:
    frames = [serialize_frame_result(frame_result) for frame_result in result.frames]
    return VideoAnalysisResponse(
        source=result.source,
        sample_rate_fps=result.sample_rate_fps,
        processed_frames=result.processed_frames,
        sampled_frames=result.sampled_frames,
        source_fps=result.source_fps,
        total_detections=result.total_detections,
        frames=frames,
        generated_event_count=result.generated_event_count,
        generated_events=[
            GeneratedEventResponse(
                event_type=event.event_type,
                camera_id=event.camera_id,
                timestamp=event.timestamp,
                track_id=event.track_id,
                estimated_speed=event.estimated_speed,
                radar_speed=event.radar_speed,
                confidence_score=event.confidence_score,
                image_evidence_path=event.image_evidence_path,
                delivery_status=event.delivery_status,
                gateway_event_id=event.gateway_event_id,
                gateway_status_code=event.gateway_status_code,
            )
            for event in result.generated_events
        ],
    )


def decode_base64_frame(frame_base64: str) -> bytes:
    try:
        return b64decode(frame_base64, validate=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "invalid_frame_base64",
                "message": "frame_base64 could not be decoded.",
            },
        ) from exc


def create_app(state: InferenceAppState | None = None) -> FastAPI:
    settings = get_settings()
    configure_logging(level=settings.log_level)
    app_state = state or InferenceAppState(settings=settings)

    app = FastAPI(
        title="ai-inference-service",
        version="0.2.0",
        description="YOLO-based vehicle detection inference service.",
    )
    app.state.inference_state = app_state

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        from time import perf_counter

        started_at = perf_counter()
        response = await call_next(request)
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            "Request completed",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(request: Request, exc: RuntimeError):
        del request
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=model_to_dict(
                ErrorResponse(
                    error=ErrorDetail(
                        code="model_initialization_failed",
                        message=str(exc),
                    )
                )
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError):
        del request
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=model_to_dict(
                ErrorResponse(
                    error=ErrorDetail(
                        code="request_validation_error",
                        message="Request validation failed.",
                        details=exc.errors(),
                    )
                )
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        del request
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            payload = ErrorResponse(error=ErrorDetail(**detail))
        else:
            payload = ErrorResponse(
                error=ErrorDetail(code="http_error", message=str(detail), details=detail)
            )
        return JSONResponse(status_code=exc.status_code, content=model_to_dict(payload))

    @app.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(
            status="ok",
            service="ai-inference-service",
            environment=settings.environment,
            lazy_model_load=settings.lazy_model_load,
            model_loaded=app_state.model_loaded,
            model_path=settings.model_path,
        )

    @app.post(
        "/frame/analyze",
        response_model=FrameAnalysisResponse,
        responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    async def analyze_uploaded_frame(
        file: UploadFile = File(...),
        source: str = Form(default="image-frame"),
        frame_index: int = Form(default=0),
        timestamp_ms: float | None = Form(default=None),
        source_fps: float | None = Form(default=None),
        sampled_fps: float | None = Form(default=None),
        captured_at: str | None = Form(default=None),
        use_tracking: bool = Form(default=False),
    ):
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "invalid_frame_content_type",
                    "message": "Uploaded frame must be an image content type.",
                },
            )

        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "empty_frame_payload",
                    "message": "Uploaded frame file is empty.",
                },
            )

        service = app_state.get_service()
        result = service.analyze_image_bytes(
            image_bytes,
            source=source or file.filename or "image-frame",
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            source_fps=source_fps,
            sampled_fps=sampled_fps,
            captured_at=captured_at,
            use_tracking=use_tracking,
        )
        return serialize_frame_result(result)

    @app.post(
        "/frame/analyze/base64",
        response_model=FrameAnalysisResponse,
        responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    async def analyze_base64_frame(request: Base64FrameAnalyzeRequest):
        image_bytes = decode_base64_frame(request.frame_base64)
        service = app_state.get_service()
        result = service.analyze_image_bytes(
            image_bytes,
            source=request.source,
            frame_index=request.frame_index,
            timestamp_ms=request.timestamp_ms,
            source_fps=request.source_fps,
            sampled_fps=request.sampled_fps,
            captured_at=request.captured_at,
            use_tracking=request.use_tracking,
        )
        return serialize_frame_result(result)

    @app.post(
        "/radar/fuse",
        responses={422: {"model": ErrorResponse}},
    )
    async def fuse_radar_event(request: RadarFuseRequest):
        event = app_state.radar_fusion.fuse_speed_violation_event(
            radar_reading=(
                RadarSpeedReading(**request.radar_speed_data)
                if request.radar_speed_data is not None
                else None
            ),
            vehicle_tracks={
                track_id: model_to_dict(track)
                for track_id, track in request.vehicle_tracks.items()
            },
            speed_limit=request.speed_limit,
            patrol_speed=request.patrol_speed,
            patrol_accel=request.patrol_accel,
        )
        return event.to_payload()

    @app.post(
        "/video/analyze",
        response_model=VideoAnalysisResponse,
        responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    async def analyze_video(request: VideoAnalyzeRequest):
        service = app_state.get_service()
        try:
            result = service.infer_video(
                source=request.source,
                sample_rate_fps=request.sample_rate_fps,
                max_frames=request.max_frames,
                use_tracking=request.use_tracking or request.speed_limit is not None,
                speed_limit=request.speed_limit,
                camera_id=request.camera_id or settings.default_camera_id,
                emit_speed_events=request.emit_speed_events,
                radar_speed=request.radar_speed,
                event_emitter=app_state.event_emitter,
                save_evidence=request.save_evidence,
            )
        except (ValueError, NotImplementedError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "invalid_video_source",
                    "message": str(exc),
                },
            ) from exc
        return serialize_video_result(result)

    return app


app = create_app()


def main():
    settings = get_settings()
    uvicorn.run(
        "service_api:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
