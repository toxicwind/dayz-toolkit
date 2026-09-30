"""
Internal event bus for decoupled event handling (High-Fidelity).
Prevents direct coupling between producers and sinks.
Includes an internal queue for buffering and asynchronous dispatch.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any, Literal

log = logging.getLogger("dayz-discord-ops.events")

EventKind = Literal[
    "status.tick",
    "killfeed.kill",
    "admin.action",
    "loot.event",
    "patch.applied",
    "patch.verified",
    "error",
]

EventHandler = Callable[[dict], Coroutine[Any, Any, None]]


def make_event_id(kind: str, payload: dict[str, Any]) -> str:
    blob = json.dumps({"kind": kind, "payload": payload}, sort_keys=True).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()[:12]


class EventBus:
    """High-fidelity async event bus using internal queues."""

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    def subscribe(self, event_type: str, handler: EventHandler):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        log.info(f"Subscribed to {event_type}")

    async def publish(self, kind: EventKind, payload: dict[str, Any]):
        from .utils.observability import get_correlation_id

        # Inject correlation ID into payload metadata if not present
        if "_correlation_id" not in payload:
            payload["_correlation_id"] = get_correlation_id()

        await self.queue.put({"type": kind, "payload": payload})

    async def start(self):
        self._running = True
        log.info("EventBus worker loop started")
        from .utils.observability import set_correlation_id

        while self._running:
            try:
                msg = await self.queue.get()
                kind = msg["type"]
                payload = msg["payload"]

                # Restore correlation context for handlers
                cid = payload.get("_correlation_id", "no-trace-bus")
                set_correlation_id(cid)

                if kind in self._handlers:
                    tasks = [handler(payload) for handler in self._handlers[kind]]
                    await asyncio.gather(*tasks, return_exceptions=True)

                self.queue.task_done()
            except Exception as e:
                log.error(f"EventBus dispatch error: {e}")

    async def stop(self):
        self._running = False
        log.info("EventBus stopped")


# Global singleton
_bus: EventBus | None = None


def get_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
        log.info("High-Fidelity EventBus initialized")
    return _bus
