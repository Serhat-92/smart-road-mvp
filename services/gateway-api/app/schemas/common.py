"""Shared API response schemas."""

from datetime import datetime
from typing import Any

from pydantic import Field

from app.core.pydantic import StrictBaseModel


class APIErrorDetail(StrictBaseModel):
    code: str = Field(..., min_length=1, max_length=120)
    message: str = Field(..., min_length=1, max_length=500)
    details: Any | None = None


class APIErrorResponse(StrictBaseModel):
    error: APIErrorDetail
    request_id: str | None = Field(default=None, max_length=64)
    timestamp: datetime
