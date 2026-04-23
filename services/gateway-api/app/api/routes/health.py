"""Health endpoints."""

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_container
from app.schemas.common import APIErrorResponse
from app.schemas.health import DatabaseStatus, HealthResponse, StorageStatus


router = APIRouter(tags=["health"])


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
    status_label = "degraded" if storage["fallback_active"] else "ok"
    return HealthResponse(
        status=status_label,
        service=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        database=DatabaseStatus(**database),
        storage=StorageStatus(**storage),
        request_path=str(request.url.path),
        request_id=getattr(request.state, "request_id", None),
    )
