import asyncio
import functools
import logging
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

T = TypeVar("T")
log = logging.getLogger("dayz-discord-ops.async_utils")


def run_async(coro: Coroutine[Any, Any, T], loop: asyncio.AbstractEventLoop | None = None) -> asyncio.Task[T]:
    """
    Schedules a coroutine to run in the given loop or the current one.
    This is the robust 'wrapper' to ensure async context exists.
    """
    if loop is None:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            log.error("No event loop found in current thread")
            raise

    return loop.create_task(coro)


def to_async(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    """Decorator to run a synchronous function in an executor."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))

    return wrapper


class AsyncBridge:
    """
    A bridge to safely call async code from non-async contexts
    or from different event loop threads.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def call(self, coro: Coroutine[Any, Any, Any]):
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.create_task, coro)
        else:
            log.warning("Loop is not running, cannot schedule coroutine")


class AsyncEventBus:
    """High-throughput async event bus using internal queues."""

    def __init__(self):
        self.subscribers: dict[str, list[Callable[[dict], Coroutine[Any, Any, None]]]] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    def subscribe(self, event_type: str, callback: Callable[[dict], Coroutine[Any, Any, None]]):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        log.info(f"Subscribed to {event_type}")

    async def publish(self, event_type: str, payload: dict):
        await self.queue.put({"type": event_type, "payload": payload})

    async def start(self):
        self._running = True
        log.info("AsyncEventBus started")
        while self._running:
            try:
                msg = await self.queue.get()
                event_type = msg["type"]
                payload = msg["payload"]

                if event_type in self.subscribers:
                    tasks = [sub(payload) for sub in self.subscribers[event_type]]
                    await asyncio.gather(*tasks, return_exceptions=True)

                self.queue.task_done()
            except Exception as e:
                log.error(f"EventBus dispatch error: {e}")

    async def stop(self):
        self._running = False
        log.info("AsyncEventBus stopped")
