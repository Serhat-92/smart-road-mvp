# Gateway API

Minimal FastAPI gateway service for field devices, events, and frame ingest.

## Structure

- `app/api/`: route registration and endpoint modules
- `app/core/`: settings and application configuration
- `app/db/`: future PostgreSQL connection management
- `app/repositories/`: persistence adapters, currently in-memory
- `app/schemas/`: Pydantic request and response models
- `app/services/`: application logic

## Run

```bash
python services/gateway-api/main.py
```

The service is intentionally persistence-light today, but the settings and DB
manager are prepared for a future PostgreSQL-backed implementation.
