"""Device endpoints."""

from fastapi import APIRouter, Depends, status

from app.dependencies import get_device_service
from app.schemas.common import APIErrorResponse
from app.schemas.device import DeviceCreate, DeviceListResponse, DeviceRead
from app.services.device_service import DeviceService


router = APIRouter(prefix="/devices", tags=["devices"])


@router.get(
    "",
    response_model=DeviceListResponse,
    responses={500: {"model": APIErrorResponse}},
)
async def list_devices(
    service: DeviceService = Depends(get_device_service),
) -> DeviceListResponse:
    items = service.list_devices()
    return DeviceListResponse(items=items, total=len(items))


@router.post(
    "",
    response_model=DeviceRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {"model": APIErrorResponse},
        500: {"model": APIErrorResponse},
    },
)
async def create_device(
    payload: DeviceCreate,
    service: DeviceService = Depends(get_device_service),
) -> DeviceRead:
    return service.register_device(payload)
