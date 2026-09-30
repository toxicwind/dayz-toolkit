import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

log = logging.getLogger("telemetry")


class Span:
    def __init__(self, name, trace_id=None, parent_id=None):
        self.name = name
        self.trace_id = trace_id or str(uuid.uuid4())
        self.span_id = str(uuid.uuid4())
        self.parent_id = parent_id
        self.start_time = None
        self.end_time = None
        self.attributes = {}

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def finish(self):
        self.end_time = time.time()
        duration = (self.end_time - self.start_time) * 1000
        event = {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "duration_ms": duration,
            "attributes": self.attributes,
            "ts": datetime.now().isoformat(),
        }
        # In a real environment, this goes to a collector (Jaeger/OTLP)
        # Here we mirror to a structured log
        log.info(f"SPAN_COMPLETE: {json.dumps(event)}")


from datetime import datetime


class Tracer:
    def __init__(self, service_name):
        self.service_name = service_name

    @asynccontextmanager
    async def start_span(self, name, parent=None):
        span = Span(name, trace_id=parent.trace_id if parent else None, parent_id=parent.span_id if parent else None)
        span.start_time = time.time()
        try:
            yield span
        finally:
            span.finish()


tracer = Tracer("dayz-discord-bot")
