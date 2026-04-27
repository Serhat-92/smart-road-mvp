"""Health endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_container
from app.schemas.common import APIErrorResponse
from app.schemas.health import DatabaseStatus, HealthResponse, RedisStatus, StorageStatus


router = APIRouter(tags=["health"])


async def _build_redis_status() -> RedisStatus:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return RedisStatus(
            enabled=False,
            connected=False,
            state="not_configured",
            last_error="REDIS_URL not set",
        )

    try:
        import redis.asyncio as redis

        client = redis.from_url(redis_url, decode_responses=True)
        await client.ping()
        await client.aclose()
        return RedisStatus(
            enabled=True,
            connected=True,
            state="connected",
            url=redis_url,
        )
    except Exception as exc:
        return RedisStatus(
            enabled=True,
            connected=False,
            state="error",
            url=redis_url,
            last_error=f"{type(exc).__name__}: {exc}",
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={500: {"model": APIErrorResponse}},
)
async def health_check(
    request: Request,
    container=Depends(get_container),
) -> HealthResponse:
    settings = container.settings
    database = container.database.status_snapshot()
    storage = container.database.storage_status_snapshot()
    redis_status = await _build_redis_status()
    status_label = (
        "degraded"
        if storage["fallback_active"] or (redis_status.enabled and not redis_status.connected)
        else "ok"
    )
    return HealthResponse(
        status=status_label,
        service=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        database=DatabaseStatus(**database),
        storage=StorageStatus(**storage),
        redis=redis_status,
        request_path=str(request.url.path),
        request_id=getattr(request.state, "request_id", None),
    )
