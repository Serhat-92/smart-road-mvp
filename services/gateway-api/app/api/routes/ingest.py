"""Ingest endpoints."""

from fastapi import APIRouter, Depends, status

from app.dependencies import get_ingest_service
from app.schemas.common import APIErrorResponse
from app.schemas.ingest import FrameIngestRequest, FrameIngestResponse
from app.services.ingest_service import IngestService


router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post(
    "/frame",
    response_model=FrameIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        422: {"model": APIErrorResponse},
        500: {"model": APIErrorResponse},
    },
)
async def ingest_frame(
    payload: FrameIngestRequest,
    service: IngestService = Depends(get_ingest_service),
) -> FrameIngestResponse:
    return service.ingest_frame(payload)
