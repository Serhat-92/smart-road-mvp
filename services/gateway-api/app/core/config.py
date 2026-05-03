"""Application settings for the gateway service."""

from dataclasses import dataclass
from functools import lru_cache
import os


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_csv(value: str | None, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    if value is None:
        return default
    items = tuple(part.strip() for part in value.split(",") if part.strip())
    return items or default


@dataclass(frozen=True)
class Settings:
    app_name: str
    version: str
    environment: str
    host: str
    port: int
    log_level: str
    cors_origins: tuple[str, ...]
    seed_demo_data: bool
    postgres_enabled: bool
    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_database: str
    postgres_echo: bool
    postgres_connect_timeout_seconds: int
    gateway_api_seed_demo_data: bool = False

    ws_enabled: bool = True
    
    jwt_secret_key: str = "smart-road-mvp-dev-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    gateway_admin_user: str = "admin"
    gateway_admin_password: str = "admin123"

    @property
    def postgres_dsn(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/"
            f"{self.postgres_database}"
        )

    @property
    def redacted_postgres_dsn(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:***@"
            f"{self.postgres_host}:{self.postgres_port}/"
            f"{self.postgres_database}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("GATEWAY_API_NAME", "gateway-api"),
        jwt_secret_key=os.getenv("GATEWAY_JWT_SECRET_KEY", "smart-road-mvp-dev-secret"),
        jwt_algorithm=os.getenv("GATEWAY_JWT_ALGORITHM", "HS256"),
        jwt_expire_minutes=int(os.getenv("GATEWAY_JWT_EXPIRE_MINUTES", "1440")),
        gateway_admin_user=os.getenv("GATEWAY_ADMIN_USER", "admin"),
        gateway_admin_password=os.getenv("GATEWAY_ADMIN_PASSWORD", "admin123"),
        version=os.getenv("GATEWAY_API_VERSION", "0.1.0"),
        environment=os.getenv("GATEWAY_API_ENV", "development"),
        ws_enabled=os.getenv("GATEWAY_WS_ENABLED", "true").lower() == "true",
        host=os.getenv("GATEWAY_API_HOST", "0.0.0.0"),
        port=int(os.getenv("GATEWAY_API_PORT", "8080")),
        log_level=os.getenv("GATEWAY_API_LOG_LEVEL", "INFO").upper(),
        cors_origins=_as_csv(
            os.getenv("GATEWAY_API_CORS_ORIGINS"),
            default=("http://localhost:5173", "http://127.0.0.1:5173"),
        ),
        seed_demo_data=_as_bool(os.getenv("GATEWAY_API_SEED_DEMO_DATA"), default=False),
        gateway_api_seed_demo_data=_as_bool(
            os.getenv("GATEWAY_API_SEED_DEMO_DATA"),
            default=False,
        ),
        postgres_enabled=_as_bool(os.getenv("POSTGRES_ENABLED"), default=False),
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        postgres_user=os.getenv("POSTGRES_USER", "postgres"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        postgres_database=os.getenv("POSTGRES_DB", "gateway_api"),
        postgres_echo=_as_bool(os.getenv("POSTGRES_ECHO"), default=False),
        postgres_connect_timeout_seconds=int(
            os.getenv("POSTGRES_CONNECT_TIMEOUT_SECONDS", "2")
        ),
    )
