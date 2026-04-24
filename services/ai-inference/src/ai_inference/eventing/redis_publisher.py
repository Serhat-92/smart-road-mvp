"""Redis-based event publisher for speed violation events.

Provides the same publish() interface as GatewayEventPublisher but sends
events to a Redis Pub/Sub channel instead of HTTP POST.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("ai_inference.eventing.redis")


class RedisEventPublisher:
    """Publish speed violation events to a Redis Pub/Sub channel."""

    def __init__(self, redis_url: str, channel: str = "speed_violations"):
        self.redis_url = redis_url
        self.channel = channel
        self._client = None

    @property
    def enabled(self) -> bool:
        return bool(self.redis_url)

    def _get_client(self):
        """Lazily create a synchronous Redis client."""
        if self._client is not None:
            return self._client
        try:
            import redis

            self._client = redis.Redis.from_url(self.redis_url, decode_responses=True)
            return self._client
        except Exception as exc:
            logger.warning("Redis client creation failed: %s", exc)
            return None

    def publish(
        self,
        *,
        event_type: str,
        camera_id: str,
        occurred_at: str,
        severity: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Publish an event to the Redis channel.

        Returns a delivery result dict with the same structure as
        GatewayEventPublisher.publish() for compatibility.
        """
        if not self.enabled:
            return {"delivery_status": "disabled"}

        client = self._get_client()
        if client is None:
            return {"delivery_status": "failed", "gateway_error": "Redis client unavailable"}

        message = {
            "event_type": event_type,
            "device_id": camera_id,
            "severity": severity,
            "payload": payload,
            "occurred_at": occurred_at,
        }

        try:
            subscriber_count = client.publish(self.channel, json.dumps(message, default=str))
            logger.info(
                "Event published to Redis",
                extra={
                    "channel": self.channel,
                    "event_type": event_type,
                    "subscriber_count": subscriber_count,
                },
            )
            return {
                "delivery_status": "sent",
                "gateway_status_code": None,
                "gateway_event_id": None,
            }
        except Exception as exc:
            logger.warning("Redis publish failed: %s", exc)
            return {"delivery_status": "failed", "gateway_error": str(exc)}
