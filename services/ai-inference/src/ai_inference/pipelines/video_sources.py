"""Video source adapters for local files today and RTSP later."""

from __future__ import annotations

from pathlib import Path
import math

from ..utils.paths import resolve_repo_path


class OpenCVVideoSource:
    """Thin wrapper around ``cv2.VideoCapture`` with normalized metadata access."""

    def __init__(self, source, *, source_name: str | None = None):
        self.source = source
        self.source_name = source_name or str(source)
        self._capture = None
        self._cv2 = None

    def open(self) -> None:
        cv2 = self._load_cv2()
        self._capture = cv2.VideoCapture(self.source)
        if not self._capture.isOpened():
            raise ValueError(f"Unable to open video source: {self.source_name}")

    def read(self):
        return self.capture.read()

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    @property
    def capture(self):
        if self._capture is None:
            raise RuntimeError("Video source has not been opened")
        return self._capture

    @property
    def fps(self) -> float | None:
        cv2 = self._load_cv2()
        raw_fps = self.capture.get(cv2.CAP_PROP_FPS)
        if raw_fps is None or not math.isfinite(raw_fps) or raw_fps <= 0:
            return None
        return float(raw_fps)

    @property
    def timestamp_ms(self) -> float | None:
        cv2 = self._load_cv2()
        raw_timestamp = self.capture.get(cv2.CAP_PROP_POS_MSEC)
        if raw_timestamp is None or not math.isfinite(raw_timestamp) or raw_timestamp < 0:
            return None
        return float(raw_timestamp)

    def _load_cv2(self):
        if self._cv2 is not None:
            return self._cv2
        try:
            import cv2
        except ImportError as exc:  # pragma: no cover - optional Docker dependency
            raise RuntimeError(
                "OpenCV is required for video processing. Install the full AI "
                "dependencies or run the local demo script from the Python environment."
            ) from exc
        self._cv2 = cv2
        return self._cv2


class LocalVideoFileSource(OpenCVVideoSource):
    """OpenCV-backed source for local video files."""

    def __init__(self, source):
        resolved_path = resolve_repo_path(source, must_exist=True)
        if not resolved_path.exists():
            raise ValueError(f"Local video file does not exist: {resolved_path}")
        if not resolved_path.is_file():
            raise ValueError(f"Local video source must be a file: {resolved_path}")
        super().__init__(str(resolved_path), source_name=str(resolved_path))
        self.path = resolved_path


class RTSPVideoSource(OpenCVVideoSource):
    """Placeholder RTSP source adapter for future expansion."""

    def __init__(self, source: str):
        if not source.lower().startswith("rtsp://"):
            raise ValueError(f"RTSP source must start with rtsp://, got: {source}")
        super().__init__(source, source_name=source)


class VideoSourceFactory:
    """Resolve a user-supplied source into a concrete source adapter."""

    def create(self, source):
        if isinstance(source, Path):
            return LocalVideoFileSource(source)

        if isinstance(source, str):
            stripped_source = source.strip()
            if not stripped_source:
                raise ValueError("Video source must not be empty")

            if stripped_source.lower().startswith("rtsp://"):
                raise NotImplementedError(
                    "RTSP support is not enabled yet. Use a local video file for now."
                )

            return LocalVideoFileSource(stripped_source)

        raise ValueError(
            "Only local video file paths are supported right now."
        )
