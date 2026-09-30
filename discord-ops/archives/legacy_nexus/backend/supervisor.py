"""
Supervisor: self-healing task management with automatic restart on crash.
Everything is async. No blocking calls.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

log = logging.getLogger("dayz-ops.supervisor")


class Supervisor:
    """Manages long-running async tasks with auto-restart on failure."""

    def __init__(self) -> None:
        self.tasks: list[asyncio.Task] = []
        self._running = False
        self.heartbeats: dict[str, float] = {}

    def start(self) -> None:
        """Start the supervisor (enable spawning)."""
        self._running = True
        log.info("Supervisor started")

    async def spawn(self, name: str, coro_factory: Callable[[], Awaitable[None]]) -> None:
        """Spawn a supervised task that auto-restarts on crash."""

        async def runner():
            backoff = 1.0
            while self._running:
                try:
                    log.info(f"task_start name={name}")
                    await coro_factory()
                    log.warning(f"task_exit name={name} (unexpected normal exit) restarting")
                except asyncio.CancelledError:
                    log.info(f"task_cancel name={name}")
                    raise
                except Exception as e:
                    log.exception(f"task_crash name={name} err={e!r}; restarting in {backoff:.1f}s")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 1.7, 60.0)  # Capped at 60s

        self._running = True
        task = asyncio.create_task(runner(), name=name)
        self.tasks.append(task)
        log.info(f"Spawned supervised task: {name}")

    async def stop(self) -> None:
        """Stop all supervised tasks."""
        self._running = False
        for t in self.tasks:
            t.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        log.info("All supervised tasks stopped")

    def heartbeat(self, name: str):
        """Update heartbeat for a task."""
        import time

        self.heartbeats[name] = time.time()

    async def monitor(self, interval: int = 30):
        """Monitor task liveness via heartbeats."""
        import time

        while self._running:
            try:
                now = time.time()
                for name, last_seen in list(self.heartbeats.items()):
                    if now - last_seen > interval * 3:
                        log.warning(f"Liveness warning: task={name} hasn't beaten in {now - last_seen:.1f}s")
                await asyncio.sleep(interval)
            except Exception as e:
                log.error(f"Supervisor monitor error: {e}")


# Global supervisor instance
_supervisor: Supervisor | None = None


async def get_supervisor() -> Supervisor:
    """Get the global supervisor instance."""
    global _supervisor
    if _supervisor is None:
        _supervisor = Supervisor()
        log.info("Supervisor initialized")
    return _supervisor
