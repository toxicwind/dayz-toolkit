import asyncio
import logging
import time
from enum import Enum
from functools import wraps

log = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    def __init__(self, name, failure_threshold=5, recovery_timeout=30):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = 0
        self._lock = asyncio.Lock()

    async def call(self, func, *args, **kwargs):
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    log.info(f"Circuit {self.name} entering HALF_OPEN state")
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise RuntimeWarning(f"Circuit {self.name} is OPEN. Blocking call.")

        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                if self.state != CircuitState.CLOSED:
                    log.info(f"Circuit {self.name} recovered to CLOSED state")
                    self.state = CircuitState.CLOSED
                    self.failures = 0
            return result
        except Exception as e:
            async with self._lock:
                self.failures += 1
                self.last_failure_time = time.time()
                log.warning(f"Circuit {self.name} failure count: {self.failures} ({e})")
                if self.failures >= self.failure_threshold:
                    if self.state != CircuitState.OPEN:
                        log.error(f"Circuit {self.name} TRIP! State changed to OPEN")
                        self.state = CircuitState.OPEN
            raise e


def circuit_breaker(cb_instance: CircuitBreaker):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await cb_instance.call(func, *args, **kwargs)

        return wrapper

    return decorator
