"""Video source adapters for local files and RTSP streams."""

from __future__ import annotations

import logging
import math
import time
from pathlib import Path

from ..utils.paths import resolve_repo_path


logger = logging.getLogger("ai_inference.video_sources")


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
    """RTSP stream source adapter with reconnection support."""

    def __init__(
        self,
        source: str,
        *,
        reconnect_attempts: int = 3,
        reconnect_delay_seconds: float = 2.0,
    ):
        if not source.lower().startswith("rtsp://"):
            raise ValueError(f"RTSP source must start with rtsp://, got: {source}")
        super().__init__(source, source_name=source)
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay_seconds = reconnect_delay_seconds

    def open(self) -> None:
        """Open the RTSP stream with retry logic."""
        cv2 = self._load_cv2()
        last_error: Exception | None = None

        for attempt in range(1, self.reconnect_attempts + 1):
            try:
                self._capture = cv2.VideoCapture(self.source)
                if self._capture.isOpened():
                    logger.info(
                        "RTSP stream opened successfully on attempt %d: %s",
                        attempt,
                        self.source_name,
                    )
                    return
                else:
                    last_error = ValueError(
                        f"RTSP stream could not be opened: {self.source_name}"
                    )
                    if self._capture is not None:
                        self._capture.release()
                        self._capture = None
            except Exception as exc:
                last_error = exc
                if self._capture is not None:
                    self._capture.release()
                    self._capture = None

            if attempt < self.reconnect_attempts:
                logger.warning(
                    "RTSP open attempt %d/%d failed, retrying in %.1fs: %s",
                    attempt,
                    self.reconnect_attempts,
                    self.reconnect_delay_seconds,
                    self.source_name,
                )
                time.sleep(self.reconnect_delay_seconds)

        raise ValueError(
            f"Unable to open RTSP source after {self.reconnect_attempts} attempts: "
            f"{self.source_name} — last error: {last_error}"
        )


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
                return RTSPVideoSource(stripped_source)

            return LocalVideoFileSource(stripped_source)

        raise ValueError(
            "Only local video file paths and rtsp:// URLs are supported."
        )
