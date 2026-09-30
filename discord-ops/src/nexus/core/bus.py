import asyncio
import logging
from typing import Callable, Dict, List, Any

log = logging.getLogger("mildlyawesome.bus")

class EventBus:
    _instance = None
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance.subscribers: Dict[str, List[Callable]] = {}
        return cls._instance

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        log.debug(f"Subscribed to {event_type}")

    async def publish(self, event_type: str, data: Any):
        if event_type in self.subscribers:
            log.debug(f"Publishing {event_type}")
            # Run all callbacks concurrently
            tasks = [cb(data) for cb in self.subscribers[event_type]]
            if tasks:
                await asyncio.gather(*tasks)

bus = EventBus()
