from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Set

import redis.asyncio as aioredis
from fastapi import WebSocket
from redis import Redis

from app.core.config import settings
from app.infra.redis.service import redis_service

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # deal_id -> set of active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._redis: aioredis.Redis | None = None
        self._pubsub_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket, deal_id: str):
        if deal_id not in self.active_connections:
            self.active_connections[deal_id] = set()
        self.active_connections[deal_id].add(websocket)
        logger.debug(f"WebSocket connected for deal {deal_id}. Total: {len(self.active_connections[deal_id])}")

    def disconnect(self, websocket: WebSocket, deal_id: str):
        if deal_id in self.active_connections:
            self.active_connections[deal_id].discard(websocket)
            if not self.active_connections[deal_id]:
                del self.active_connections[deal_id]
            logger.debug(f"WebSocket disconnected for deal {deal_id}")

    async def broadcast_to_deal(self, deal_id: str, message: dict):
        """Broadcasts a JSON message to all connections subscribed to a specific deal_id."""
        if deal_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[deal_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Error sending message to socket: {e}")
                    disconnected.append(connection)
            
            for conn in disconnected:
                self.disconnect(conn, deal_id)

    async def start_redis_listener(self):
        """
        Starts a background task that listens to Redis Pub/Sub for 'deal_updates' channel.
        Includes basic reconnection logic.
        """
        self._pubsub_task = asyncio.create_task(self._listen_loop())

    async def _listen_loop(self):
        """Internal loop with reconnection logic."""
        logger.info("Starting Redis Pub/Sub listener...")
        while True:
            try:
                self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
                pubsub = self._redis.pubsub()
                await pubsub.subscribe("deal_updates")
                logger.info("Subscribed to 'deal_updates' channel")

                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            # message["data"] is string because decode_responses=True
                            data_str = message.get("data")
                            if not data_str: continue

                            # Try to parse as JSON first
                            if isinstance(data_str, str):
                                try:
                                    data = json.loads(data_str)
                                except json.JSONDecodeError:
                                    # Fallback: maybe it's just a raw deal_id string? Or unexpected format.
                                    logger.warning(f"Received non-JSON message: {data_str}")
                                    continue
                            else:
                                data = data_str

                            if isinstance(data, dict):
                                deal_id = data.get("deal_id")
                                if deal_id:
                                    await self.broadcast_to_deal(deal_id, data)
                        except Exception as e:
                            logger.error(f"Error processing Redis message: {e}", exc_info=True)

            except asyncio.CancelledError:
                logger.info("Redis listener task cancelled.")
                if self._redis:
                    await self._redis.close()
                break
            except Exception as e:
                logger.error(f"Redis listener connection error: {e}. Reconnecting in 5s...")
                if self._redis:
                    try: await self._redis.close()
                    except: pass
                await asyncio.sleep(5)

    async def stop_redis_listener(self):
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass


manager = ConnectionManager()


def notify_deal_update(deal_id: str, event_type: str = "updated"):
    """
    Helper to publish a deal update to Redis.
    Uses sync redis client from redis_service to support sync contexts (RQ, etc).
    """
    try:
        # Get sync connection
        redis_conn = redis_service.get_connection(decode_responses=False)
        message = json.dumps({"deal_id": deal_id, "type": event_type})
        redis_conn.publish("deal_updates", message)
    except Exception as e:
        logger.error(f"Failed to publish deal update for {deal_id}: {e}")
