import asyncio
import logging
from src.mildlyawesome.services.parsers.base import LogEvent
from src.mildlyawesome.core.bus import bus

log = logging.getLogger("mildlyawesome.streamer")

class LogStreamer:
    def __init__(self, settings):
        self.settings = settings
        self._listeners = []

    async def _notify_listeners(self, event: LogEvent):
        """Internal hook used by selfplay_driver and real ingestors."""
        log.info(f"Streaming Event: {event.message}")
        # Use the singleton bus with string key
        await bus.publish("log.ingested", event)

# Singleton access
_streamer = None
def get_streamer(settings=None):
    global _streamer
    if not _streamer:
        if settings:
            _streamer = LogStreamer(settings)
        else:
            # Fallback for when settings aren't passed but streamer is needed
            pass
    return _streamer
