#!/bin/sh
set -e

if [ "$POSTGRES_ENABLED" = "true" ]; then
  echo "[entrypoint] Running database migrations..."
  python -m alembic -c /app/infra/alembic.ini upgrade head
  echo "[entrypoint] Migrations complete."
fi

exec python main.py
