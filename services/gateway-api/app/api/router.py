"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes.devices import router as devices_router
from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.ingest import router as ingest_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(events_router)
api_router.include_router(devices_router)
api_router.include_router(ingest_router)
