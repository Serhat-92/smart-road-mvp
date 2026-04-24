"""FastAPI app factory for the gateway service."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import install_exception_handlers
from app.api.router import api_router
from app.container import build_container
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


logger = get_logger("gateway_api.http")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    container = build_container(settings)
    app.state.container = container
    await container.database.connect()

    # ── Redis ViolationConsumer ─────────────────────────────────────
    consumer = None
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        from app.workers.violation_consumer import ViolationConsumer

        consumer = ViolationConsumer(redis_url=redis_url)
        await consumer.start(
            repo=container.event_service.repository,
            db_manager=container.database,
        )
        logger.info(
            "Redis ViolationConsumer started",
            extra={"redis_url": redis_url},
        )
    else:
        logger.warning(
            "REDIS_URL env var not set — Redis ViolationConsumer not started. "
            "Events will only be received via HTTP POST.",
        )

    logger.info(
        "Gateway API started",
        extra={
            "host": settings.host,
            "port": settings.port,
            "storage_backend": container.database.storage_backend,
            "database_state": container.database.state,
        },
    )
    try:
        yield
    finally:
        if consumer is not None:
            await consumer.stop()
            logger.info("Redis ViolationConsumer stopped")
        await container.database.disconnect()
        logger.info("Gateway API stopped", extra={"database_state": container.database.state})


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(
        service_name=settings.app_name,
        environment=settings.environment,
        level=settings.log_level,
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Gateway service for devices, events, and frame ingest.",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id

        started_at = perf_counter()
        response = await call_next(request)
        duration_ms = round((perf_counter() - started_at) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        log_level = "warning" if response.status_code >= 400 else "info"
        getattr(logger, log_level)(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_host": request.client.host if request.client else None,
            },
        )
        return response

    install_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
