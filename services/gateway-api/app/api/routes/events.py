"""Event endpoints."""

from fastapi import APIRouter, Depends, status

from app.dependencies import get_event_service
from app.schemas.common import APIErrorResponse
from app.schemas.event import EventCreate, EventListResponse, EventRead
from app.services.event_service import EventService


router = APIRouter(prefix="/events", tags=["events"])


@router.get(
    "",
    response_model=EventListResponse,
    responses={500: {"model": APIErrorResponse}},
)
async def list_events(
    service: EventService = Depends(get_event_service),
) -> EventListResponse:
    items = service.list_events()
    return EventListResponse(items=items, total=len(items))


@router.post(
    "",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {"model": APIErrorResponse},
        500: {"model": APIErrorResponse},
    },
)
async def create_event(
    payload: EventCreate,
    service: EventService = Depends(get_event_service),
) -> EventRead:
    return service.create_event(payload)
