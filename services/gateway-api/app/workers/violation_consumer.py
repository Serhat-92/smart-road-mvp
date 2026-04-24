"""Redis consumer for speed violation events.

Subscribes to a Redis Pub/Sub channel and persists incoming SpeedViolationAlert
events into the event repository (in-memory or PostgreSQL depending on mode).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

logger = logging.getLogger("gateway_api.workers.violation_consumer")


class ViolationConsumer:
    """Subscribe to Redis speed_violations channel and write events to the repository."""

    def __init__(self, redis_url: str, channel: str = "speed_violations"):
        self.redis_url = redis_url
        self.channel = channel
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self, repo, db_manager) -> None:
        """Start consuming events in a background task."""
        self._running = True
        self._task = asyncio.create_task(self._consume_loop(repo, db_manager))
        logger.info(
            "ViolationConsumer started",
            extra={"channel": self.channel, "redis_url": self.redis_url},
        )

    async def stop(self) -> None:
        """Stop the consumer gracefully."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("ViolationConsumer stopped")

    async def _consume_loop(self, repo, db_manager) -> None:
        """Main consume loop with automatic reconnection."""
        import redis.asyncio as aioredis

        while self._running:
            try:
                client = aioredis.from_url(self.redis_url, decode_responses=True)
                pubsub = client.pubsub()
                await pubsub.subscribe(self.channel)
                logger.info("Subscribed to Redis channel: %s", self.channel)

                async for message in pubsub.listen():
                    if not self._running:
                        break
                    if message["type"] != "message":
                        continue

                    try:
                        data = json.loads(message["data"])
                        await self._handle_event(data, repo, db_manager)
                    except Exception as exc:
                        logger.warning(
                            "Failed to process Redis message: %s",
                            exc,
                            extra={"channel": self.channel},
                        )

                await pubsub.unsubscribe(self.channel)
                await client.aclose()

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(
                    "Redis connection lost, reconnecting in 5s: %s",
                    exc,
                    extra={"channel": self.channel},
                )
                await asyncio.sleep(5)

    async def _handle_event(self, data: dict, repo, db_manager) -> None:
        """Process a single event message from Redis."""
        now = datetime.now(timezone.utc)
        payload = data.get("payload", {})

        record = {
            "id": uuid4(),
            "event_type": data.get("event_type", "speed.violation_alert"),
            "device_id": data.get("device_id", ""),
            "severity": data.get("severity", "warning"),
            "payload": payload,
            "occurred_at": data.get("occurred_at", now.isoformat()),
            "created_at": now,
        }

        if db_manager.connected and db_manager.storage_backend == "postgres":
            try:
                async for session in db_manager.get_session():
                    await repo.add_async(session, record)
                    break
            except Exception as exc:
                logger.warning("PostgreSQL write failed, using in-memory: %s", exc)
                repo.add(record)
        else:
            repo.add(record)

        logger.info(
            "Event consumed from Redis",
            extra={
                "event_type": record["event_type"],
                "device_id": record["device_id"],
                "severity": record["severity"],
            },
        )
