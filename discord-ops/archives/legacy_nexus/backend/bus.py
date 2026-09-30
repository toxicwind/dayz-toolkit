"""
Redis-backed Event Bus for real-time communication.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional

from redis import asyncio as aioredis

log = logging.getLogger("event_bus")

class EventBus:
    _instance: Optional["EventBus"] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(EventBus, cls).__new__(cls)
        return cls._instance

    def __init__(self, redis_url: str = "redis://localhost:19106"):
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self._initialized = True

    async def connect(self):
        """Connect to Redis and initialize PubSub"""
        if self.redis:
            return

        try:
            self.redis = aioredis.from_url(self.redis_url, decode_responses=True)
            self.pubsub = self.redis.pubsub()
            log.info(f"📡 EventBus connected to Redis at {self.redis_url}")
        except Exception as e:
            log.error(f"Failed to connect to EventBus: {e}")

    async def publish(self, channel: str, message: Dict[str, Any]):
        """Publish a message to a channel"""
        if not self.redis:
            await self.connect()
        
        try:
            await self.redis.publish(channel, json.dumps(message))
        except Exception as e:
            log.error(f"Failed to publish to {channel}: {e}")

    async def subscribe(self, channel: str, callback: Callable[[Dict[str, Any]], Any]):
        """Subscribe to a channel and trigger a callback for each message"""
        if not self.pubsub:
            await self.connect()
        
        await self.pubsub.subscribe(channel)
        
        async def listen():
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                    except Exception as e:
                        log.error(f"Error in EventBus subscriber for {channel}: {e}")
        
        asyncio.create_task(listen())
        log.info(f"👂 Subscribed to EventBus channel: {channel}")

def get_bus() -> EventBus:
    return EventBus()
