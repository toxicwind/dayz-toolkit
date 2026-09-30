from __future__ import annotations

import asyncio
import logging
import traceback
import os
import shutil
import uuid
import threading
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, Header, HTTPException, Body, BackgroundTasks
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.coder import PickleCoder
from redis import asyncio as aioredis
from pydantic import BaseModel
import orjson

from .discord_ingest_store import store as ingest_store
from .globals import set_bot, get_bot

# Log Correlation ID Setup
import logging as _logging
if not getattr(_logging, "_correlation_id_factory_installed", False):
    _base_factory = _logging.getLogRecordFactory()
    def _record_factory(*args, **kwargs):
        r = _base_factory(*args, **kwargs)
        if not hasattr(r, "correlation_id"):
            r.correlation_id = "-"
        return r
    _logging.setLogRecordFactory(_record_factory)
    _logging._correlation_id_factory_installed = True

log = logging.getLogger("dayz-discord-ops.api")

app = FastAPI(
    title="DayZ December Mission Control",
    description="Refactored Modular API for DayZ Operations.",
    version="2.1.0-MODULAR",
)

# --- Middleware ---
from starlette.middleware.base import BaseHTTPMiddleware
from .utils.observability import get_correlation_id, set_correlation_id

class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        cid = request.headers.get("X-Correlation-ID") or get_correlation_id()
        set_correlation_id(cid)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response

app.add_middleware(CorrelationMiddleware)

# --- Modular Router Integration ---
from src.mildlyawesome.routers import (
    discord_ops, server_ops, mission_ops, logs_ops,
    debug_ops, chronos_ops, config_ops, community_ops,
    system_ops, shell_ops, analytics_ops, ops_tools,
    intelligence_ops
)

app.include_router(discord_ops.router)
app.include_router(server_ops.router)
app.include_router(mission_ops.router)
app.include_router(logs_ops.router)
app.include_router(debug_ops.router)
app.include_router(chronos_ops.router)
app.include_router(config_ops.router)
app.include_router(community_ops.router)
app.include_router(system_ops.router)
app.include_router(shell_ops.router)
app.include_router(analytics_ops.router)
app.include_router(ops_tools.router)
app.include_router(intelligence_ops.router)

@app.on_event("startup")
async def startup_event():
    # Redis Cache initialization
    try:
        redis = aioredis.from_url("redis://localhost:19106", encoding="utf8", decode_responses=False)
        FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache", coder=PickleCoder)
        log.info("🚀 Redis Cache initialized")
    except Exception as e:
        log.error(f"Failed to initialize Redis Cache: {e}")

    # Initialize shared stores
    try:
        from .todo_store import store as todo_store
        await todo_store.initialize()
        from .engagement_store import store as eng_store
        await eng_store.initialize()
        log.info("Shared stores initialized")
    except Exception as e:
        log.error(f"Store initialization failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    log.info("API shutting down...")

def start_api(host: str = "0.0.0.0", port: int = 8080):
    import uvicorn
    log.warning("Starting API server on %s:%s", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info", proxy_headers=False)
