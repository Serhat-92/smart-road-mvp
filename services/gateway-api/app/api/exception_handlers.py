"""Global exception handlers for consistent API responses."""

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.errors import GatewayAPIError
from app.core.logging import get_logger
from app.schemas.common import APIErrorDetail, APIErrorResponse


logger = get_logger("gateway_api.errors")


def _build_error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details=None,
) -> JSONResponse:
    payload = APIErrorResponse(
        error=APIErrorDetail(code=code, message=message, details=details),
        request_id=getattr(request.state, "request_id", None),
        timestamp=datetime.now(timezone.utc),
    )
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


async def handle_gateway_api_error(request: Request, exc: GatewayAPIError) -> JSONResponse:
    logger.warning(
        "Gateway API error",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "error_code": exc.code,
        },
    )
    return _build_error_response(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def handle_request_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return _build_error_response(
        request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="request_validation_error",
        message="Request validation failed.",
        details=exc.errors(),
    )


async def handle_pydantic_validation_error(
    request: Request,
    exc: ValidationError,
) -> JSONResponse:
    return _build_error_response(
        request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="payload_validation_error",
        message="Payload validation failed.",
        details=exc.errors(),
    )


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    message = detail if isinstance(detail, str) else "Request failed."
    return _build_error_response(
        request,
        status_code=exc.status_code,
        code="http_error",
        message=message,
        details=None if isinstance(detail, str) else detail,
    )


async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
            "method": request.method,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
    )
    return _build_error_response(
        request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_server_error",
        message="The server could not complete the request.",
    )


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(GatewayAPIError, handle_gateway_api_error)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    app.add_exception_handler(ValidationError, handle_pydantic_validation_error)
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_exception)
