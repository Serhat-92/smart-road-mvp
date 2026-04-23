"""Application-specific error types for consistent API responses."""

from typing import Any


class GatewayAPIError(Exception):
    """Base error type surfaced through the API exception handlers."""

    status_code = 500
    code = "internal_server_error"
    message = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Any | None = None,
    ):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details


class EventPayloadValidationError(GatewayAPIError):
    status_code = 422
    code = "invalid_event_payload"
    message = "Event payload validation failed."


class IngestValidationError(GatewayAPIError):
    status_code = 422
    code = "invalid_ingest_request"
    message = "Frame ingest request validation failed."
