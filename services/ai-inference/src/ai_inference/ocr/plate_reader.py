"""License plate OCR reader using EasyOCR with lazy model loading.

The EasyOCR model is large (~100MB+), so the Reader is initialized lazily
on the first call to read() rather than at construction time.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from event_contracts.models import BoundingBox

logger = logging.getLogger("ai_inference.ocr.plate_reader")

# Türk plaka formatı: 06 ABC 1234, 34 A 12, 01 AB 123 vb.
_TURKISH_PLATE_PATTERN = re.compile(r"^[0-9]{2}\s?[A-Z]{1,3}\s?[0-9]{2,4}$")


class PlateReader:
    """Read license plates from cropped vehicle bounding boxes.

    The EasyOCR Reader is NOT created in __init__. It is lazily initialized
    on the first read() call via self._reader (starts as None).
    """

    def __init__(self, languages: list[str] | None = None, gpu: bool = False):
        self._languages = languages or ["tr", "en"]
        self._gpu = gpu
        # Lazy-load: model yüklenmez, ilk read() çağrısında oluşturulur
        self._reader = None

    def _ensure_reader(self) -> None:
        """Initialize the EasyOCR Reader if not already done."""
        if self._reader is not None:
            return
        try:
            import easyocr

            logger.info(
                "Initializing EasyOCR Reader (languages=%s, gpu=%s) — first read() call",
                self._languages,
                self._gpu,
            )
            self._reader = easyocr.Reader(self._languages, gpu=self._gpu)
        except ImportError:
            logger.warning(
                "easyocr is not installed. PlateReader.read() will always return None."
            )
        except Exception as exc:
            logger.error("Failed to initialize EasyOCR Reader: %s", exc)

    def read(self, frame_bgr: np.ndarray, bbox: BoundingBox) -> str | None:
        """Crop the bounding box region from the frame and attempt OCR.

        Returns a Turkish plate string if the result matches the expected
        format, otherwise None.
        """
        self._ensure_reader()
        if self._reader is None:
            return None

        try:
            # Crop bounding box from frame
            x1 = max(int(round(bbox.x1)), 0)
            y1 = max(int(round(bbox.y1)), 0)
            x2 = min(int(round(bbox.x2)), frame_bgr.shape[1])
            y2 = min(int(round(bbox.y2)), frame_bgr.shape[0])

            if x2 <= x1 or y2 <= y1:
                return None

            cropped = frame_bgr[y1:y2, x1:x2]
            if cropped.size == 0:
                return None

            # EasyOCR okuma
            results = self._reader.readtext(cropped, detail=0)
            if not results:
                return None

            # Sonuçları birleştir, normalize et, regex ile kontrol et
            raw_text = " ".join(results).strip().upper()
            # Türk harflerine uyarlama: yaygın OCR hataları
            normalized = raw_text.replace("İ", "I").replace("Ö", "O").replace("Ü", "U")
            # Sadece alfanümerik ve boşluk bırak
            cleaned = re.sub(r"[^A-Z0-9\s]", "", normalized).strip()
            # Fazla boşlukları tek boşluk yap
            cleaned = re.sub(r"\s+", " ", cleaned)

            if _TURKISH_PLATE_PATTERN.match(cleaned):
                logger.info("Plate detected: %s", cleaned)
                return cleaned

            # Boşluk olmadan da dene
            compact = cleaned.replace(" ", "")
            if _TURKISH_PLATE_PATTERN.match(compact):
                logger.info("Plate detected (compact): %s", compact)
                return compact

            logger.debug(
                "OCR text '%s' does not match Turkish plate format", cleaned
            )
            return None

        except Exception as exc:
            logger.warning("PlateReader.read() failed: %s", exc)
            return None
