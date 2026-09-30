"""
Observability Utility
Provides standardized logging and correlation ID context.
"""

import contextvars
import logging
import uuid

# Context variable for Correlation ID
_correlation_id_ctx = contextvars.ContextVar("correlation_id", default=None)


def get_correlation_id() -> str:
    """Get current correlation ID or generate a new one."""
    cid = _correlation_id_ctx.get()
    if not cid:
        cid = str(uuid.uuid4())
        _correlation_id_ctx.set(cid)
    return cid


def set_correlation_id(cid: str):
    """Set the correlation ID for the current context."""
    _correlation_id_ctx.set(cid)


class StructuredLogger(logging.Logger):
    """Logger that injects correlation ID and formats as JSON (optional, or just structured text)."""

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        if extra is None:
            extra = {}

        cid = _correlation_id_ctx.get()
        if cid:
            extra["correlation_id"] = cid

        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)


# Helper to wrap generic loggers if needed, or just use standard logging with a Filter
class CorrelationFilter(logging.Filter):
    """Injects correlation_id into log records."""

    def filter(self, record):
        if not hasattr(record, "correlation_id"):
            record.correlation_id = _correlation_id_ctx.get() or "-"
        return True


class SafeFormatter(logging.Formatter):
    """Formatter that ensures correlation_id exists."""
    def format(self, record):
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "-"
        return super().format(record)


def configure_observability():
    """Configure root logger to use correlation filter with defensive formatting."""
    root_logger = logging.getLogger()
    
    # Check if already added
    for f in root_logger.filters:
        if isinstance(f, CorrelationFilter):
            return

    f = CorrelationFilter()
    root_logger.addFilter(f)

    log_format = "%(asctime)s [%(correlation_id)s] %(levelname)s %(name)s: %(message)s"
    formatter = SafeFormatter(log_format)
    
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
    
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
