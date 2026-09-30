import json
import logging
from collections import deque
from dataclasses import asdict, dataclass

from fastapi import WebSocket

log = logging.getLogger("dayz-discord-ops.social-streamer")


@dataclass
class SocialEvent:
    timestamp: str
    source: str  # e.g., "discord"
    user: str
    message: str
    channel: str | None = None
    avatar_url: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class SocialStreamer:
    def __init__(self):
        self.clients: set[WebSocket] = set()
        self.buffer: deque[SocialEvent] = deque(maxlen=100)

    async def broadcast(self, event: SocialEvent):
        """Broadcast a social event to all connected clients."""
        self.buffer.append(event)
        if not self.clients:
            return

        message = event.to_json()
        disconnected = set()
        for client in self.clients:
            try:
                await client.send_text(message)
            except Exception:
                disconnected.add(client)

        for client in disconnected:
            self.clients.discard(client)

    async def handle_client(self, websocket: WebSocket):
        """Handle a new WebSocket client connection."""
        # NOTE: accept() is now called by the parent route handler in api.py
        self.clients.add(websocket)
        log.info(f"Social client connected. Total: {len(self.clients)}")

        try:
            # Send buffer history
            for event in self.buffer:
                await websocket.send_text(event.to_json())

            # Keep alive
            while True:
                await websocket.receive_text()
        except Exception:
            pass
        finally:
            self.clients.discard(websocket)
            log.info("Social client disconnected.")


_streamer = SocialStreamer()


def get_social_streamer() -> SocialStreamer:
    return _streamer
