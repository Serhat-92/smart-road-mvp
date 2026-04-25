"""Event endpoints."""

from __future__ import annotations

import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.core.errors import EventPayloadValidationError
from app.core.security import get_current_user
from app.dependencies import get_db_session, get_event_service, get_repository_mode
from app.schemas.common import APIErrorResponse
from app.schemas.event import EventCreate, EventListResponse, EventRead
from app.services.event_service import EventService


logger = logging.getLogger("gateway_api.events.routes")

router = APIRouter(prefix="/events", tags=["events"])


@router.get(
    "",
    response_model=EventListResponse,
    responses={500: {"model": APIErrorResponse}},
)
async def list_events(
    service: EventService = Depends(get_event_service),
    mode: Literal["postgres", "memory"] = Depends(get_repository_mode),
    session=Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> EventListResponse:
    if mode == "postgres" and session is not None:
        items = await service.list_events_async(session)
    else:
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
    mode: Literal["postgres", "memory"] = Depends(get_repository_mode),
    session=Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> EventRead:
    try:
        if mode == "postgres" and session is not None:
            event = await service.create_event_async(payload, session)
        else:
            event = service.create_event(payload)
    except EventPayloadValidationError as exc:
        logger.warning(
            "Event payload validation failed: %s",
            exc,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
                "request_id": str(uuid.uuid4()),
            },
        )
    except Exception as exc:
        logger.error(
            "Failed to create event: %s: %s",
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": f"Event creation failed: {type(exc).__name__}: {exc}"},
        )

    # Broadcast to WebSocket clients
    try:
        from app.api.routes.websocket import manager
        from app.core.pydantic import model_to_dict
        import asyncio
        asyncio.create_task(manager.broadcast(model_to_dict(event)))
    except Exception as exc:
        logger.warning("WebSocket broadcast failed: %s", exc)

    return event
