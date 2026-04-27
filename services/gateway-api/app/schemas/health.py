"""Health response schemas."""

from typing import Optional

from app.core.pydantic import StrictBaseModel


class DatabaseStatus(StrictBaseModel):
    enabled: bool
    connected: bool
    state: str
    dsn: Optional[str] = None
    last_error: Optional[str] = None


class StorageStatus(StrictBaseModel):
    backend: str
    fallback_active: bool
    reason: Optional[str] = None


class RedisStatus(StrictBaseModel):
    enabled: bool
    connected: bool
    state: str
    url: Optional[str] = None
    last_error: Optional[str] = None


class HealthResponse(StrictBaseModel):
    status: str
    service: str
    version: str
    environment: str
    database: DatabaseStatus
    storage: StorageStatus
    redis: RedisStatus
    request_path: str
    request_id: Optional[str] = None
