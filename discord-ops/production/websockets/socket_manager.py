import logging
import socketio
import redis.asyncio as aioredis
import os
import json

log = logging.getLogger("dayz-ops.socket")

class SocketManager:
    def __init__(self, redis_url=None):
        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins="*",
            logger=True,
            engineio_logger=True
        )
        self.app = socketio.ASGIApp(self.sio)
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = None
        self._pubsub_task = None

    async def start(self):
        log.info(f"Connecting to Redis at {self.redis_url}")
        self.redis = aioredis.from_url(self.redis_url)
        self._pubsub_task = asyncio.create_task(self._listen_to_redis())

        @self.sio.event
        async def connect(sid, environ):
            log.info(f"Client connected: {sid}")

        @self.sio.event
        async def disconnect(sid):
            log.info(f"Client disconnected: {sid}")

    async def _listen_to_redis(self):
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe("events.*")
        
        async for message in pubsub.listen():
            if message['type'] == 'pmessage':
                channel = message['channel'].decode()
                data = json.loads(message['data'].decode())
                # Broadcast specific events to web clients
                if channel.startswith("events.killfeed"):
                    await self.sio.emit("killfeed_update", data)
                elif channel.startswith("events.status"):
                    await self.sio.emit("status_update", data)

    async def broadcast(self, event_type, data):
        """Internal broadcast to all connected web clients."""
        await self.sio.emit(event_type, data)
