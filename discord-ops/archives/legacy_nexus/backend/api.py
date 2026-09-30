from __future__ import annotations

import asyncio
import logging

# [LOGRECORD_DEFAULTS_CORRELATION_ID]
import logging as _logging
import shutil
import uuid
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

# Guard against hot-reload re-registering the factory
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
    title="DayZ Discord Ops Mission Control",
    description="Premium December 2025 standard API for DayZ server management, analytics, and automated ops.",
    version="2.0.0-SIGMA",
    contact={
        "name": "Ops Intelligence Team",
        "url": "http://localhost:3000",
    },
    license_info={
        "name": "Proprietary",
    },
)

# Expose ingest store to HTTP diagnostics
# Expose ingest store to HTTP diagnostics
_ingest_store = ingest_store


@app.on_event("startup")
async def startup_event():
    # Initialize Redis Cache
    try:
        redis = aioredis.from_url("redis://localhost:19106", encoding="utf8", decode_responses=False)
        FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache", coder=PickleCoder)
        log.info("🚀 Redis Cache initialized on port 19106 with PickleCoder")
    except Exception as e:
        log.error(f"Failed to initialize Redis Cache: {e}")

    # Initialize shared stores for standalone API mode
    try:
        from .todo_store import store as todo_store

        await todo_store.initialize()
        log.info("TodoStore initialized via API startup")
    except Exception as e:
        log.error(f"Failed to initialize TodoStore: {e}")

    try:
        from .engagement_store import store as eng_store

        await eng_store.initialize()
        log.info("EngagementStore initialized via API startup")
    except Exception as e:
        log.error(f"Failed to initialize EngagementStore: {e}")


# CORS - TEMPORARILY DISABLED FOR WS DEBUG

# app.add_middleware(
#     CORSMiddleware,
#     allow_origin_regex=".*",
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

log.warning("API initialized WITHOUT CORS middleware for WS debugging")

# Observability Middleware
from starlette.middleware.base import BaseHTTPMiddleware

from .utils.observability import get_correlation_id, set_correlation_id


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Extract from header or generate
        cid = request.headers.get("X-Correlation-ID") or get_correlation_id()
        set_correlation_id(cid)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response


app.add_middleware(CorrelationMiddleware)

# Routers are now discovered dynamically in the loop below.


# 2. Dynamic Module API Discovery (modules/*/api.py)
import importlib

# --- Fleet / Multi-Tenant Context ---
from .fleet import get_registry

@app.get("/api/fleet")
async def list_fleet_services():
    """Returns a list of all available fleet services (tenants)."""
    registry = get_registry()
    services = registry.list_services()
    return {"services": services}

@app.get("/api/fleet/{service_id}/status")
async def get_fleet_status(service_id: str, background_tasks: BackgroundTasks):
    """Returns high-level status for a specific fleet context with SWR."""
    registry = get_registry()
    settings = registry.get_service(service_id)
    if not settings:
        return {"status": "error", "message": "Service not found"}
    
    # Check cache first (Manual SWR pattern)
    cache_key = f"swr_status_{service_id}"
    cached_data = await FastAPICache.get_backend().get(cache_key)
    
    if cached_data:
        # Trigger background update
        background_tasks.add_task(update_status_cache, service_id, cache_key)
        return orjson.loads(cached_data)

    # If not in cache, fetch synchronously and cache
    data = await update_status_cache(service_id, cache_key)
    return data

async def update_status_cache(service_id: str, cache_key: str):
    """Fetches real status from Nitrado SDK and updates cache."""
    from .nitrado_sdk_client import create_client_from_config
    
    try:
        client = create_client_from_config(service=service_id)
        status = await client.get_status()
        details = await client.get_gameserver_details()
        
        data = {
            "id": service_id,
            "status": status,
            "details": details.get("data", {}).get("gameserver", {}),
            "last_updated": datetime.utcnow().isoformat(),
            "source": "nitrado_sdk"
        }
        
        await FastAPICache.get_backend().set(cache_key, orjson.dumps(data), expire=60)
        return data
    except Exception as e:
        log.error(f"Failed to update status cache for {service_id}: {e}")
        return {"status": "error", "message": str(e)}

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """Real-time log streaming via WebSocket with EventBus integration."""
    await websocket.accept()
    from .bus import get_bus
    bus = get_bus()
    await bus.connect()
    
    log.info(f"🔌 WebSocket log subscriber connected: {websocket.client}")

    async def log_callback(data):
        try:
            await websocket.send_json(data)
        except Exception:
            # Client likely disconnected
            pass

    # Subscribe to all log channels
    await bus.subscribe("logs.*", log_callback)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except Exception:
        log.info(f"🔌 WebSocket log subscriber disconnected: {websocket.client}")

# --- Module Discovery ---
modules_dir = Path(__file__).parent.parent / "modules"
if modules_dir.exists():
    for module_path in modules_dir.iterdir():
        if module_path.is_dir() and (module_path / "api.py").exists():
            try:
                module_name = f"modules.{module_path.name}.api"
                mod = importlib.import_module(module_name)
                if hasattr(mod, "router"):
                    app.include_router(mod.router)
                    log.info(f"Registered modular API router: {module_name}")
            except Exception as e:
                log.error(f"Failed to register modular API {module_path.name}: {e}")

# 3. Register Core Nitrado API (Hyper-Integrated)
try:
    from .api_nitrado import router as nitrado_router
    app.include_router(nitrado_router)
    log.info("Registered Core Nitrado API router")
except ImportError as e:
    log.error(f"Failed to register Core Nitrado API: {e}")

# 4. Register MCP Protocol Endpoint (Agent Gateway Integration)
try:
    from .mcp import router as mcp_router
    app.include_router(mcp_router)
    log.info("Registered MCP Protocol router at /mcp")
except ImportError as e:
    log.error(f"Failed to register MCP router: {e}")

from .social_streamer import get_social_streamer
from .websocket_routes import websocket_logs_endpoint


# WebSocket handlers are centralized above or in modular routers.


@app.websocket("/ws/social")
async def websocket_social(websocket: WebSocket):
    """WebSocket endpoint for live Discord social feed"""
    log.warning(f"[WS_PROBE] /ws/social handler ENTERED, client={websocket.client}")
    await websocket.accept()
    log.warning("[WS_PROBE] /ws/social ACCEPTED")
    streamer = get_social_streamer()
    await streamer.handle_client(websocket)


@app.websocket("/ws/probe")
async def websocket_probe(websocket: WebSocket):
    """Minimal WebSocket probe for substrate testing"""
    log.warning(f"[WS_PROBE] /ws/probe ENTERED, client={websocket.client}")
    await websocket.accept()
    await websocket.send_text("probe_ok")
    log.warning("[WS_PROBE] /ws/probe sent probe_ok")
    await websocket.close()


# Background task control
_background_task_running = False
_background_task = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/debug/mock_social")
async def mock_social(user: str = "TestUser", message: str = "Hello from AIS!"):
    from datetime import datetime

    from .social_streamer import SocialEvent, get_social_streamer

    streamer = get_social_streamer()
    event = SocialEvent(timestamp=datetime.utcnow().isoformat(), source="debug", user=user, message=message)
    await streamer.broadcast(event)
    return {"status": "dispatched"}


@app.post("/debug/emit_event")
async def debug_emit_event(event_type: str, payload: dict):
    """Inject an event directly into the High-Fidelity Event Fabric."""
    from .events import get_bus

    bus = get_bus()
    await bus.publish(event_type, payload)
    await bus.publish(event_type, payload)
    return {"status": "published", "type": event_type, "payload": payload}


@app.post("/debug/inject_log")
async def debug_inject_log(line: str, source: str = "nitrado"):
    """Inject a raw log line into LogStreamer to test parsing and correlation."""
    from .log_streamer import get_streamer

    streamer = get_streamer()

    # We cheat a bit and use the generic parser, then broadcast
    # This simulates a real log coming from FTP/WS
    event = streamer._parse_generic_log_line(line, source, "adm" if "ADM" in line else "rpt")

    if event:
        await streamer._broadcast_event(event)
        return {"status": "injected", "cid": event.correlation_id, "parsed": event.to_json()}
    return {"status": "ignored", "reason": "parser returned None"}


class PatchAnnouncementRequest(BaseModel):
    title: str
    version: str
    description: str = ""
    changes: list[str] = []


@app.post("/ops/announce_patch")
async def announce_patch_endpoint(req: PatchAnnouncementRequest):
    """Trigger a manual patch announcement to Discord."""
    from .events import get_bus

    bus = get_bus()

    payload = req.dict()
    # Add timestamp if missing
    payload["timestamp"] = datetime.utcnow().isoformat()

    await bus.publish("patch.applied", payload)
    return {"status": "published", "target": "changelog"}


# === Mission Management Endpoints ===
class MissionValidateRequest(BaseModel):
    path: str


class MissionScaleRequest(BaseModel):
    path: str
    nominal_mult: float
    min_mult: float | None = None
    round_mode: str = "ceil"


@app.post("/mission/validate")
async def validate_mission_endpoint(req: MissionValidateRequest):
    """Validate DayZ mission structure and CE configuration"""
    try:
        from pathlib import Path

        from .mission_tools import validate_mission

        findings = validate_mission(Path(req.path))
        return {
            "status": "ok",
            "errors": [f.as_line() for f in findings if f.level == "ERROR"],
            "warnings": [f.as_line() for f in findings if f.level == "WARN"],
            "total": len(findings),
        }
    except Exception as e:
        log.error(f"Mission validation failed: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/mission/diagnose")
async def diagnose_mission_endpoint(req: MissionValidateRequest):
    """Run opinionated diagnostics on mission"""
    try:
        from pathlib import Path

        from .mission_tools import diagnose_mission

        notes = diagnose_mission(Path(req.path))
        return {"status": "ok", "notes": [{"title": n.title, "detail": n.detail} for n in notes]}
    except Exception as e:
        log.error(f"Mission diagnostics failed: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/mission/scale")
async def scale_mission_endpoint(req: MissionScaleRequest):
    """Scale nominal/min counts in types.xml"""
    try:
        from pathlib import Path

        from .mission_tools import scale_types_xml

        target_dir = Path(req.path)
        types_path = None
        for cand in [target_dir / "types.xml", target_dir / "db" / "types.xml"]:
            if cand.exists():
                types_path = cand
                break

        if not types_path:
            return {"status": "error", "message": "Could not locate types.xml"}

        res = scale_types_xml(types_path, req.nominal_mult, req.min_mult, req.round_mode)
        return {"status": "ok", "touched": res.touched, "changed": res.changed, "path": str(types_path)}
    except Exception as e:
        log.error(f"Mission scaling failed: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/server/status")
async def get_server_status_endpoint():
    """High-fidelity merger of Nitrado (Account) and A2S (Live UDP) state."""
    if not _bot_ref:
        return {"status": "offline", "data": {}}

    cog = _bot_ref.get_cog("StatusCog")
    if not cog:
        return {"status": "error", "message": "Status module not loaded"}

    status = cog.service.get_cached_status()
    if not status:
        status, _, _ = await cog.service.update()

    # Get health metrics if available
    from .health_monitor import get_monitor
    monitor = get_monitor()
    health_summary = monitor.get_health_summary()

    return {
        "status": status.status,
        "data": {
            "status": status.status,
            "ip": _bot_ref.settings.dayz_host or "85.190.152.232",  # Fallback to configured/detected IP
            "port": _bot_ref.settings.dayz_query_port or "2302",
            "version": status.version,
            "query": {
                "player_current": status.players,
                "player_max": status.max_players,
                "server_version": status.version,
                "map": status.mission,
                "server_name": status.server_name,
            },
            "health": health_summary.get("metrics"),
            "last_updated": datetime.now().isoformat(),
        },
    }


@app.get("/backend/status")
async def get_bot_status():
    """Discord Bot operational telemetry."""
    if not _bot_ref:
        return {"status": "offline", "guild": "N/A", "latency": "N/A"}

    # Calculate latency in ms
    latency_ms = round(_bot_ref.latency * 1000) if _bot_ref.latency else 0

    # Find primary guild name
    guild_name = "Unknown"
    if _bot_ref.settings.discord_guild_id:
        guild = _bot_ref.get_guild(_bot_ref.settings.discord_guild_id)
        if guild:
            guild_name = guild.name
    elif _bot_ref.guilds:
        guild_name = _bot_ref.guilds[0].name

    return {
        "status": "online" if not _bot_ref.is_closed() else "offline",
        "guild": guild_name,
        "latency": f"{latency_ms}ms",
        "uptime": getattr(_bot_ref, "uptime_str", "N/A"),
        "extensions": len(_bot_ref.extensions),
    }


@app.get("/config")
async def get_sanitized_config():
    """Expose dynamic provenance and configuration."""
    from .config import load_settings

    settings = load_settings()

    version = "1.28-SIGMA"
    region = "UNKNOWN"

    if _bot_ref:
        cog = _bot_ref.get_cog("StatusCog")
        if cog:
            status = cog.service.get_cached_status()
            if status:
                version = status.version
                region = status.region

    return {
        "org_id": settings.org_id,
        "server_name": settings.server_name,
        "platform": settings.platform.upper() if settings.platform else "XBOX",
        "region": region.upper(),
        "status": "ONLINE",
        "version": version,
        "patches_src_dir": settings.patches_src_dir,
        "mission_path": settings.mission_path,
        "vanilla_path": settings.vanilla_path,
    }


@app.post("/server/restart")
async def restart_server_endpoint():
    from .config import load_settings
    from .nitrado_api import NitradoAPIClient

    settings = load_settings()
    service_id = settings.nitrado_service_id
    if not service_id:
        return {"status": "error", "message": "Nitrado Service ID not configured"}

    client = NitradoAPIClient(settings.nitrado_token or "")
    res = client.restart_server(service_id)
    return res


@app.post("/server/stop")
async def stop_server_endpoint():
    from .config import load_settings
    from .nitrado_api import NitradoAPIClient

    settings = load_settings()
    service_id = settings.nitrado_service_id
    if not service_id:
        return {"status": "error", "message": "Nitrado Service ID not configured"}

    client = NitradoAPIClient(settings.nitrado_token or "")
    res = client.stop_server(service_id)
    return res


class BanRequest(BaseModel):
    gamertag: str


@app.post("/server/ban")
async def ban_player_endpoint(req: BanRequest):
    from .config import load_settings
    from .nitrado_api import NitradoAPIClient

    settings = load_settings()
    service_id = settings.nitrado_service_id
    if not service_id:
        return {"status": "error", "message": "Nitrado Service ID not configured"}

    client = NitradoAPIClient(settings.nitrado_token or "")
    res = client.ban_player(service_id, req.gamertag)
    return res


@app.get("/security/scan")
async def security_scan():
    """Run security check and return results."""
    import asyncio
    import json

    try:
        proc = await asyncio.create_subprocess_exec(
            "python3",
            "backend/scripts/run_security_check.py",
            "dupe",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return {"status": "error", "error": stderr.decode()}

        try:
            data = json.loads(stdout.decode())
            return data
        except json.JSONDecodeError:
            return {"status": "error", "error": "Invalid JSON output", "raw": stdout.decode()}

    except Exception as e:
        return {"status": "error", "error": str(e)}


# Global reference to bot instance, injected by backend.py
_bot_ref = None

# --- Protocol SIGMA: Log Verification ---


@app.get("/logs/probe")
async def probe_logs():
    """SIGMA-1: Connectivity Check"""
    if not _bot_ref:
        return {"status": "error", "message": "Bot instance not linked"}
    cog = _bot_ref.get_cog("LogIntelligence")
    if cog:
        return await cog.probe()
    # Fallback to log_streamer
    from .log_streamer import get_streamer

    streamer = get_streamer()
    return {
        "status": "ok",
        "source": "log_streamer",
        "buffer_size": len(streamer.log_buffer),
        "clients": len(streamer.clients),
    }


@app.post("/logs/sync")
async def sync_logs_manual():
    """SIGMA-2: Force Ingestion"""
    if not _bot_ref:
        return {"status": "error", "message": "Bot instance not linked"}
    cog = _bot_ref.get_cog("LogIntelligence")
    if cog:
        return await cog.ingest_once()
    # Fallback - log_streamer is already polling, just return status
    from .log_streamer import get_streamer

    streamer = get_streamer()
    return {
        "status": "ok",
        "source": "log_streamer",
        "message": "Log streamer is continuously polling FTP/Nitrado",
        "buffer_size": len(streamer.log_buffer),
    }


@app.get("/logs")
async def get_logs_sigma(limit: int = 50):
    """SIGMA-3: Serving - returns recent log events"""
    if _bot_ref:
        cog = _bot_ref.get_cog("LogIntelligence")
        if cog:
            return {"events": cog.get_recent_events(limit=limit)}

    # Fallback to log_streamer buffer
    from dataclasses import asdict

    from .log_streamer import get_streamer

    streamer = get_streamer()
    events = list(streamer.log_buffer)[-limit:]
    return {"events": [asdict(e) for e in events], "source": "log_streamer", "total_buffered": len(streamer.log_buffer)}


class LogReadRequest(BaseModel):
    path: str


@app.post("/logs/content")
async def read_log_content(req: LogReadRequest):
    from .config import load_settings
    from .ftp_client import FTPClient

    settings = load_settings()
    if not settings.ftp_host:
        return {"error": "FTP not configured"}

    client = FTPClient(settings.ftp_host, settings.ftp_port, settings.ftp_user, settings.ftp_password)
    try:
        client.connect()
        # Security check: prevent directory traversal or reading outside of allowed paths if needed
        # For now, we trust the input but in production should sanitize req.path
        content = client.read_file(req.path)
        if content is None:
            return {"error": "Failed to read file"}
        return {"content": content}
    finally:
        client._close()


@app.get("/nitrado/logs")
async def list_nitrado_logs():
    from .config import load_settings
    from .nitrado_api import NitradoAPIClient

    settings = load_settings()
    if not settings.nitrado_token:
        return {"error": "Nitrado API token not configured"}

    client = NitradoAPIClient(settings.nitrado_token)
    service_id = settings.nitrado_service_id
    if not service_id:
        return {"error": "Nitrado Service ID not configured"}

    # Nitrado logs are specific to the game server instance
    logs = await client.get_logs_list(service_id)
    return {"files": [{"name": f, "path": f} for f in logs]}


@app.post("/nitrado/logs/content")
async def read_nitrado_log_content(req: LogReadRequest):
    from .config import load_settings
    from .nitrado_api import NitradoAPIClient

    settings = load_settings()
    if not settings.nitrado_token:
        return {"error": "Nitrado API token not configured"}

    client = NitradoAPIClient(settings.nitrado_token)
    service_id = settings.nitrado_service_id
    if not service_id:
        return {"error": "Nitrado Service ID not configured"}

    content = await client.download_file(service_id, req.path)
    if content is None:
        return {"error": "Failed to download log from Nitrado"}
    return {"content": content}


class PlayerActionRequest(BaseModel):
    gamertag: str


class ChannelMatrixResponse(BaseModel):
    channels: list[dict]
    last_seq: int
    tracks: list[str]


@app.get("/players")
async def get_players():
    """Get list of online players from Nitrado API (Xbox compatible)"""
    from .config import load_settings
    from .nitrado_api import NitradoAPIClient

    settings = load_settings()
    service_id = settings.nitrado_service_id

    if not settings.nitrado_token:
        return {"players": []}

    try:
        client = NitradoAPIClient(settings.nitrado_token)
        details = await client.get_gameserver_details(service_id)

        if details and details.get("status") == "success":
            gameserver = details.get("data", {}).get("gameserver", {})
            query = gameserver.get("query", {})

            # Get player list from query data
            players_list = query.get("players", [])
            player_current = query.get("player_current", 0)
            player_max = query.get("player_max", 0)

            # Format players for frontend
            formatted_players = []
            for player in players_list:
                formatted_players.append(
                    {
                        "gamertag": player.get("name", "Unknown"),
                        "status": "online",
                        "last_seen": None,  # Real-time data
                        "score": player.get("score", 0),
                        "duration": player.get("duration", 0),
                    }
                )

            return {"players": formatted_players, "player_count": player_current, "max_players": player_max}
    except Exception as e:
        log.error(f"Failed to fetch players from Nitrado: {e}")

    return {"players": [], "player_count": 0, "max_players": 0}


# --- Discord Channel Matrix ---


class ChannelMatrixQuery(BaseModel):
    since_seq: int = 0
    channel_ids: list[int] | None = None


@app.get("/discord/diagnostics", response_model=ChannelMatrixResponse)
async def discord_diagnostics():
    """Return channel validation status + last event cursors."""
    status = _ingest_store.get_status_matrix()
    tracks = []
    if _bot_ref and getattr(_bot_ref, "_tracked_channels", None):
        tracks = [f"{k}:{v}" for k, v in _bot_ref._tracked_channels().items() if v]
    return ChannelMatrixResponse(channels=status, last_seq=_ingest_store._seq, tracks=tracks)


@app.post("/discord/events")
async def discord_events(query: ChannelMatrixQuery):
    events = _ingest_store.get_events_since(query.since_seq, query.channel_ids)
    return {"events": [e.__dict__ for e in events], "last_seq": _ingest_store._seq}


@app.post("/players/kick")
async def kick_player(req: PlayerActionRequest):
    """Kick endpoint disabled (RCON unavailable on Console). Use Ban instead."""
    return {"status": "error", "message": "Kick not supported on Console (RCON unavailable). Use Ban."}


@app.get("/server/economy")
async def get_economy_config():
    """Get types.xml loot configuration"""
    from .config import load_settings
    from .ftp_client import FTPClient

    settings = load_settings()
    if not settings.ftp_host:
        return {"error": "FTP not configured"}

    client = FTPClient(settings.ftp_host, settings.ftp_port, settings.ftp_user, settings.ftp_password)
    try:
        client.connect()
        # Read types.xml from mission folder
        mission_path = settings.ftp_mission_path
        content = client.read_file(f"{mission_path}/db/types.xml")
        if content is None:
            return {"error": "Failed to read types.xml"}
        return {"content": content, "format": "xml"}
    finally:
        client._close()


@app.get("/mission/files")
async def list_mission_files():
    """List XML files in the mission db directory"""
    from .config import load_settings
    from .ftp_client import FTPClient

    # Try local mission path from config
    settings = load_settings()
    mission_path = Path(settings.mission_path)
    db_path = mission_path / "db"

    # Also check container-specific path as fallback
    container_staging = Path("staging/ezstreet/dayzxb_missions/dayzOffline.chernarusplus")
    container_db = container_staging / "db"

    try:
        # First try config path
        if db_path.exists():
            files = [f for f in db_path.iterdir() if f.is_file() and f.name.endswith(".xml")]
            return {"files": sorted([f.name for f in files]), "source": "local"}
        # Fallback to container staging path
        elif container_db.exists():
            files = [f for f in container_db.iterdir() if f.is_file() and f.name.endswith(".xml")]
            return {"files": sorted([f.name for f in files]), "source": "container_staging"}
    except Exception as e:
        log.warning(f"Local mission files failed: {e}")

    # Fallback to FTP
    try:
        settings = load_settings()
        if not settings.ftp_host:
            return {"error": "Mission files not accessible (no local mount, no FTP)", "files": []}

        client = FTPClient(settings.ftp_host, settings.ftp_port, settings.ftp_user, settings.ftp_password)
        client.connect()
        mission_path = settings.ftp_mission_path
        files_raw = client.list_files(f"{mission_path}/db/")
        client._close()

        # Extract filenames from FTP list
        files = [f["name"] for f in files_raw if f["name"].endswith(".xml")]
        return {"files": sorted(files), "source": "ftp"}
    except Exception as e:
        log.error(f"Failed to list mission files: {e}")
        return {"error": str(e), "files": []}


@app.get("/mission/files/{filename}")
async def get_mission_file(filename: str):
    """Read a specific XML file from db directory"""
    from .config import load_settings

    settings = load_settings()
    mission_path = Path(settings.mission_path)
    db_path = mission_path / "db"
    file_path = db_path / filename

    # Security traversal check
    if ".." in filename or filename.startswith("/"):
        return {"error": "Invalid filename"}

    try:
        content = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
        return {"filename": filename, "content": content}
    except Exception as e:
        log.error(f"Failed to read file {filename}: {e}")
        return {"error": str(e)}


class FileUpdateRequest(BaseModel):
    content: str
    backup: bool = True


@app.post("/mission/files/{filename}")
async def update_mission_file(filename: str, req: FileUpdateRequest):
    """Update a specific XML file"""
    import os

    from .config import load_settings

    settings = load_settings()
    mission_path = Path(settings.mission_path)
    db_path = mission_path / "db"
    file_path = db_path / filename
    backup_path = file_path.with_suffix(file_path.suffix + ".bak")

    if ".." in filename or filename.startswith("/"):
        return {"error": "Invalid filename"}

    try:
        # Create backup if requested
        if req.backup and os.path.exists(file_path):
            shutil.copy2(file_path, backup_path)

        await asyncio.to_thread(file_path.write_text, req.content, "utf-8")

        return {"status": "success", "message": f"Updated {filename}"}
    except Exception as e:
        log.error(f"Failed to update file {filename}: {e}")
        return {"status": "error", "message": str(e)}


# Keep existing economy endpoints for backward compat / script triggering
@app.get("/server/economy/config")
async def get_economy_settings():
    """Get economy configuration from JSON"""
    import json
    import os
    from pathlib import Path

    # Config is now in staging volume, separated from game files
    if os.path.exists("staging"):
        base_path = Path("staging")
    else:
        # Local dev fallback
        repo_root = Path(__file__).parent.parent.parent
        base_path = repo_root / "staging"

    config_path = base_path / "EZStreet_ServerConfig.json"

    try:
        data = await asyncio.to_thread(json.loads, config_path.read_text())
        return data
    except Exception as e:
        log.error(f"Failed to read economy config: {e}")
        return {"error": str(e), "economy": {}}


class EconomyUpdateRequest(BaseModel):
    loot_multiplier: float
    lifetime_multiplier: float
    zombie_max: int
    animal_max: int


@app.post("/server/economy/config")
async def update_economy_settings(req: EconomyUpdateRequest):
    """Update economy configuration and run apply script"""
    import asyncio
    import json

    # Determine paths based on environment
    import os
    from pathlib import Path

    if os.path.exists("staging"):
        base_path = Path("staging")
    else:
        # Local dev fallback: assumed to be run from repo root
        # Try to find dayz_discord_ops_repo/staging
        current_dir = Path(__file__).parent
        # Go up to repo root
        repo_root = current_dir.parent.parent
        base_path = repo_root / "staging"

    config_path = base_path / "EZStreet_ServerConfig.json"
    script_path = base_path / "configeconomy.py"

    # Read existing to preserve other fields like "organization"
    try:
        current_data = await asyncio.to_thread(json.loads, config_path.read_text())
    except Exception:
        current_data = {"organization": "EZStreet", "version": "1.0", "economy": {}}

    current_data["economy"] = req.dict()

    try:
        await asyncio.to_thread(config_path.write_text, json.dumps(current_data, indent=2))

        # Run the script
        # This script applies the config to the /app/missions volume or local equivalent
        cmd = ["python3", str(script_path)]
        log.info(f"Running hook script: {cmd}")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return {
                "status": "warning",
                "message": "Config saved but script failed",
                "stderr": stderr.decode(),
                "stdout": stdout.decode(),
            }

        return {"status": "success", "message": "Configuration updated and applied"}
    except Exception as e:
        log.error(f"Failed to update economy config: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/stats/history")
async def get_stats_history():
    """Get historical server stats for charts"""
    from .config import load_settings
    from .database import get_db_connection

    settings = load_settings()
    stats = []

    try:
        conn = await get_db_connection(settings)
        if not conn:
            return {"stats": []}

        def _fetch():
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT timestamp, player_count, max_players
                    FROM server_stats
                    WHERE timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)
                    ORDER BY timestamp ASC
                    """
                )
                return cursor.fetchall()

        rows = await asyncio.to_thread(_fetch)
        for row in rows:
            ts = row[0]
            stats.append(
                {
                    "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts) if ts else None,
                    "player_count": row[1],
                    "max_players": row[2],
                }
            )
    except Exception as e:
        log.error(f"Failed to fetch stats history: {e}")

    return {"stats": stats}


@app.get("/intelligence/emergent")
async def get_emergent_intelligence():
    """
    Get 30+ emergent feature metrics (Heatmaps, Economy, Anomalies).
    Powered by LogIntelligence Engine.
    """
    if not _bot_ref:
        return {"status": "error", "message": "Bot instance not linked"}

    cog = _bot_ref.get_cog("LogIntelligence")
    if not cog:
        return {"status": "error", "message": "LogIntelligence system offline"}

    return cog.intel_engine.get_emergent_intelligence()


# --- Intelligence API ---
# (Intelligence logic now lives in modules/intelligence)


@app.post("/intelligence/scan_logs")
async def scan_logs_for_intelligence():
    """
    Legacy placeholder. Log scanning is now handled by the modular Intelligence service.
    """
    return {"status": "ok", "message": "Log scanning is now handled by modules/intelligence."}


@app.get("/killfeed")
async def get_killfeed(limit: int = 50):
    from .config import load_settings

    settings = load_settings()
    conn = await get_db_connection(settings)
    if not conn:
        return {"kills": []}

    try:

        def _fetch():
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM combat_logs ORDER BY timestamp DESC LIMIT %s", (limit,))
                return cursor.fetchall()

        rows = await asyncio.to_thread(_fetch)
        return {"kills": rows}
    except Exception as e:
        log.error(f"Failed to fetch killfeed: {e}")
        return {"kills": []}
    finally:
        conn.close()


# --- Economy Intelligence ---


@app.get("/server/economy/intelligence/clusters")
async def get_economy_clusters():
    from pathlib import Path

    from .config import load_settings
    from .economy_intelligence import EconomyIntelligence

    settings = load_settings()
    mission_path = Path(settings.mission_path)
    # Path to types.xml in mission volume
    path = mission_path / "db" / "types.xml"

    intel = EconomyIntelligence(path)
    return intel.get_smart_clusters()


@app.get("/server/economy/intelligence/validate")
async def validate_economy():
    from pathlib import Path

    from .economy_intelligence import EconomyIntelligence

    path = Path("missions/dayzOffline.chernarusplus/db/types.xml")
    if not path.exists():
        path = (
            Path(__file__).parent.parent.parent / "dayzxb_missions" / "dayzOffline.chernarusplus" / "db" / "types.xml"
        )

    intel = EconomyIntelligence(path)
    return {"warnings": intel.validate_logic()}


# Global bot reference for status access
_bot_ref = None


@app.get("/backend/status")
async def get_bot_status():
    if not _bot_ref:
        return {"status": "inactive", "message": "API running standalone"}

    guild = _bot_ref.get_guild(_bot_ref.settings.discord_guild_id)
    return {
        "status": "online" if _bot_ref.is_ready() else "connecting",
        "name": str(_bot_ref.user),
        "guild": guild.name if guild else "Unknown",
        "guild_id": _bot_ref.settings.discord_guild_id,
        "latency": f"{round(_bot_ref.latency * 1000)}ms",
    }


@app.get("/audit/channels")
async def audit_channels_endpoint():
    """Audit Discord channels via API"""
    if not _bot_ref:
        return {"status": "error", "message": "Bot not connected"}

    cog = _bot_ref.get_cog("ChannelAudit")
    if not cog:
        return {"status": "error", "message": "ChannelAudit cog not loaded"}

    guild = _bot_ref.get_guild(_bot_ref.settings.discord_guild_id)
    if not guild:
        # Fallback to any guild
        if _bot_ref.guilds:
            guild = _bot_ref.guilds[0]
        else:
            return {"status": "error", "message": "Guild not found"}

    try:
        data = cog.scan_guild(guild)
        # Convert dataclasses to simple dicts
        simple_results = []
        for r in data["results"]:
            simple_results.append(
                {
                    "id": r.channel_id,
                    "name": r.channel_name,
                    "type": r.channel_type,
                    "category": r.category,
                    "matched_feature": r.matched_feature,
                    "suggestions": r.suggestions,
                }
            )
        data["results"] = simple_results
        return data
    except Exception as e:
        log.error(f"Audit failed: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/simulation/trigger")
async def trigger_simulation(mode: str = "full_demo", count: int = 3):
    """Trigger SelfPlayDriver simulation"""
    if not _bot_ref:
        return {"status": "error", "message": "Bot not connected"}

    cog = _bot_ref.get_cog("SelfPlayDriver")
    if not cog:
        return {"status": "error", "message": "SelfPlayDriver cog not loaded"}

    try:
        instruction = {"mode": mode, "count": count}
        # Run in background to avoid blocking the API response
        asyncio.run_coroutine_threadsafe(cog.execute_instruction(instruction), _bot_ref.loop)
        return {"status": "success", "message": f"Simulation '{mode}' started with count={count}"}
    except Exception as e:
        log.error(f"Simulation failed: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/a2s/status")
async def get_a2s_status():
    if not _bot_ref:
        return {"status": "inactive", "message": "API running standalone"}

    # Access internal metrics or last info
    # Assuming bot has a way to expose this.
    # Looking at backend.py, it updates prometheus metrics.
    # We can check A2S_UP value or similar if we imported it,
    # but accessing _bot_ref state is better if possible.
    # backend.py doesn't seem to store `last_info` publicly on self,
    # but `stat_tick` updates it.

    # Let's return a simple status based on A2S_UP metric which is imported in backend.py
    # Actually, we can just import the metrics here too.
    from .metrics import A2S_PLAYERS, A2S_UP

    is_up = A2S_UP._value.get() == 1.0
    players = A2S_PLAYERS._value.get()

    return {
        "status": "online" if is_up else "offline",
        "players": players,
        "message": "Cached status from backend",
    }


@app.get("/backend/logs")
async def get_bot_logs(limit: int = 50):
    from .config import load_settings
    from .database import get_db_connection

    settings = load_settings()
    logs = []
    try:
        conn = await get_db_connection(settings)
        if not conn:
            return {"logs": []}

        def _fetch():
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT timestamp, type, message, severity FROM activity_logs ORDER BY timestamp DESC LIMIT %s",
                    (limit,),
                )
                return cursor.fetchall()

        rows = await asyncio.to_thread(_fetch)
        for row in rows:
            ts = row["timestamp"]
            logs.append(
                {
                    "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts) if ts else None,
                    "type": row["type"],
                    "message": row["message"],
                    "severity": row["severity"],
                }
            )
    except Exception as e:
        log.error(f"Failed to fetch bot logs: {e}")

    return {"logs": logs}


@app.get("/config/globals")
async def get_globals_config():
    """Get globals.xml configuration (zombies, animals, loot damage)"""
    from .dayz_config_manager import DayZConfigManager

    try:
        manager = DayZConfigManager()
        globals_data = manager.get_globals()

        return {
            "status": "success",
            "globals": {
                "ZombieMaxCount": globals_data.get("ZombieMaxCount", 1000),
                "AnimalMaxCount": globals_data.get("AnimalMaxCount", 200),
                "LootDamageMin": globals_data.get("LootDamageMin", 0.0),
                "LootDamageMax": globals_data.get("LootDamageMax", 0.0),
            },
        }
    except Exception as e:
        log.error(f"Failed to read globals.xml: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/config/globals")
async def update_globals_config(req: dict):
    """Update globals.xml configuration via Patching System"""
    from .dayz_config_manager import DayZConfigManager

    try:
        manager = DayZConfigManager()
        updates = {}

        if "ZombieMaxCount" in req:
            updates["ZombieMaxCount"] = int(req["ZombieMaxCount"])
        if "AnimalMaxCount" in req:
            updates["AnimalMaxCount"] = int(req["AnimalMaxCount"])
        if "LootDamageMin" in req:
            updates["LootDamageMin"] = float(req["LootDamageMin"])
        if "LootDamageMax" in req:
            updates["LootDamageMax"] = float(req["LootDamageMax"])

        success = manager.update_globals(updates)

        if success:
            uploaded = manager.upload_to_server(
                str(manager.globals_xml), "/dayzxb_missions/dayzOffline.chernarusplus/db/globals.xml"
            )
            return {"status": "success", "message": "globals.xml updated", "uploaded": uploaded}
        else:
            return {"status": "error", "message": "Failed to update globals.xml"}
    except Exception as e:
        log.error(f"Failed to update globals.xml: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/config/gameplay")
async def get_gameplay_config():
    """Get gameplay configuration from cfggameplay.json"""
    from .dayz_config_manager import DayZConfigManager

    try:
        manager = DayZConfigManager()
        gameplay = manager.get_gameplay()
        return {"status": "success", "gameplay": gameplay}
    except Exception as e:
        log.error(f"Failed to read gameplay config: {e}")
        return {"status": "error", "message": str(e), "gameplay": {}}


@app.post("/config/gameplay")
async def update_gameplay_config(req: dict):
    """Update gameplay configuration"""
    from .dayz_config_manager import DayZConfigManager

    try:
        manager = DayZConfigManager()
        success = manager.update_gameplay(req)

        if success:
            uploaded = manager.upload_to_server(
                str(manager.mission_path / "cfggameplay.json"),
                "/dayzxb_missions/dayzOffline.chernarusplus/cfggameplay.json",
            )
            return {"status": "success", "message": "Gameplay config updated", "uploaded": uploaded}
        return {"status": "error", "message": "Failed to update gameplay config"}
    except Exception as e:
        log.error(f"Failed to update gameplay config: {e}")
        return {"status": "error", "message": str(e)}


@app.delete("/config/gameplay")
async def reset_gameplay_config():
    """Reset gameplay configuration to vanilla/provenance base"""
    from .dayz_config_manager import DayZConfigManager

    try:
        manager = DayZConfigManager()
        success = manager.clear_gameplay_patches()
        if success:
            uploaded = manager.upload_to_server(
                str(manager.mission_path / "cfggameplay.json"),
                "/dayzxb_missions/dayzOffline.chernarusplus/cfggameplay.json",
            )
            return {"status": "success", "message": "Gameplay config reset to base", "uploaded": uploaded}
        else:
            return {"status": "error", "message": "Failed to reset gameplay config"}
    except Exception as e:
        log.error(f"Failed to reset gameplay config: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/config/weather")
async def get_weather_config():
    """Get weather configuration from cfgweather.xml"""
    from .dayz_config_manager import DayZConfigManager

    try:
        manager = DayZConfigManager()
        weather = manager.get_weather()
        return {"status": "success", "weather": weather}
    except Exception as e:
        log.error(f"Failed to read weather config: {e}")
        return {"status": "error", "message": str(e), "weather": {}}


@app.post("/config/weather")
async def update_weather_config(req: dict):
    """Update weather configuration"""
    from .dayz_config_manager import DayZConfigManager

    try:
        manager = DayZConfigManager()
        success = manager.update_weather(req)

        if success:
            uploaded = manager.upload_to_server(
                str(manager.mission_path / "cfgweather.xml"),
                "/dayzxb_missions/dayzOffline.chernarusplus/cfgweather.xml",
            )
            return {"status": "success", "message": "Weather config updated", "uploaded": uploaded}
        else:
            return {"status": "error", "message": "Failed to update weather config"}
    except Exception as e:
        log.error(f"Failed to update weather config: {e}")
        return {"status": "error", "message": str(e)}


# Background tasks are now managed within modular cogs.


@app.get("/analytics/leaderboard")
async def get_leaderboard(limit: int = 10):
    """Top players by kills and KD ratio"""
    from .config import load_settings
    from .database import get_db_connection

    settings = load_settings()
    try:
        conn = await get_db_connection(settings)
        if not conn:
            return {"players": []}

        def _fetch():
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT last_known_name as name, player_id, kills, deaths,
                           (kills / NULLIF(deaths, 0)) as kd
                    FROM player_profiles
                    ORDER BY kills DESC, kd DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return cursor.fetchall()

        rows = await asyncio.to_thread(_fetch)
        return {"players": rows}
    except Exception as e:
        log.error(f"Leaderboard failed: {e}")
        return {"players": [], "error": str(e)}


@app.get("/analytics/hotzones")
async def get_hotzones():
    """Kill heatmap data (clustered locations)"""
    from .config import load_settings
    from .database import get_db_connection

    settings = load_settings()
    try:
        conn = await get_db_connection(settings)
        if not conn:
            return {"hotzones": []}

        def _fetch():
            with conn.cursor() as cursor:
                # Binning positions into 100m zones for heatmap
                cursor.execute(
                    """
                    SELECT ROUND(pos_x, -2) as x, ROUND(pos_z, -2) as z, COUNT(*) as weight
                    FROM combat_logs
                    WHERE pos_x IS NOT NULL AND pos_z IS NOT NULL
                    GROUP BY x, z
                    HAVING weight >= 1
                    LIMIT 200
                    """
                )
                return cursor.fetchall()

        rows = await asyncio.to_thread(_fetch)
        return {"hotzones": rows}
    except Exception as e:
        log.error(f"Hotzones failed: {e}")
        return {"hotzones": [], "error": str(e)}


@app.post("/ops/backup")
async def trigger_backup():
    """Trigger the server backup script"""
    import subprocess
    from pathlib import Path

    script_path = Path(__file__).parent / "scripts" / "backup_server.py"

    try:
        # Run script in background to prevent timeout
        subprocess.Popen(["python3", str(script_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"status": "success", "message": "Backup job dispatched to background"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/webhooks/vpp")
async def vpp_webhook(payload: dict):
    """
    Receives events from VPPAdminTools Webhook.
    Mimics a Discord webhook endpoint to receive high-velocity events.
    """
    from .events import get_bus

    bus = get_bus()

    event_type = payload.get("Event", "unknown")
    log.info(f"Received VPP Webhook: {event_type}")

    if event_type == "PlayerKill":
        await bus.publish(
            "killfeed.kill",
            {
                "killer": payload.get("KillerName"),
                "victim": payload.get("VictimName"),
                "weapon": payload.get("Weapon"),
                "distance": payload.get("Distance"),
                "location": payload.get("Location"),
                "source": "vpp_webhook",
            },
        )
    else:
        await bus.publish("vpp.event", payload)

    return {"status": "success"}


# --- Finalizing API Setup ---
@app.on_event("startup")
async def startup_event():
    """Start background tasks on API startup"""
    global _background_task_running, _background_task

    log.info("API startup: background tasks DISABLED for debugging...")
    # _background_task_running = True
    # _background_task = asyncio.create_task(intelligence_background_task())
    # log.info("Background intelligence scanner started")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks on API shutdown"""
    global _background_task_running, _background_task

    log.info("API shutdown: stopping background tasks...")
    _background_task_running = False

    if _background_task:
        _background_task.cancel()
        try:
            await _background_task
        except asyncio.CancelledError:
            pass

    log.info("Background tasks stopped")


def start_api(host: str = "0.0.0.0", port: int = 8080):
    import uvicorn

    log.warning("Starting API server on %s:%s (Proxy Headers DISABLED for WS debug)", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info", proxy_headers=False)


# Test endpoints for Discord live updates
@app.post("/test/killfeed")
async def test_killfeed(payload: dict):
    """Trigger test killfeed event via EventBus"""
    if _bot_ref and getattr(_bot_ref, "event_bus", None):
        await _bot_ref.event_bus.publish("killfeed.kill", payload)
        return {"status": "ok", "event": "killfeed.kill", "payload": payload}
    return {"status": "error", "message": "Bot/EventBus not ready"}


@app.post("/test/admin_action")
async def test_admin_action(payload: dict):
    """Trigger test admin action via EventBus"""
    if _bot_ref and getattr(_bot_ref, "event_bus", None):
        await _bot_ref.event_bus.publish("admin.action", payload)
        return {"status": "ok", "event": "admin.action", "payload": payload}
    return {"status": "error", "message": "Bot/EventBus not ready"}


@app.post("/test/loot_event")
async def test_loot_event(payload: dict):
    """Trigger test loot event via EventBus"""
    if _bot_ref and getattr(_bot_ref, "event_bus", None):
        await _bot_ref.event_bus.publish("loot.event", payload)
        return {"status": "ok", "event": "loot.event", "payload": payload}
    return {"status": "error", "message": "Bot/EventBus not ready"}


@app.post("/test/ghost_replay")
async def test_ghost_replay(limit: int = 5):
    """
    Fetch real historical kills from DB and replay them as 'GHOST' events.
    Used for verifying killfeed logic without waiting for live kills.
    """
    from .config import load_settings
    from .database import get_db_connection
    from .events import get_bus

    settings = load_settings()
    bus = get_bus()

    try:
        conn = await get_db_connection(settings)
        if not conn:
            return {"status": "error", "message": "DB not connected"}

        def _fetch():
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM combat_logs ORDER BY timestamp DESC LIMIT %s", (limit,))
                return cursor.fetchall()

        rows = await asyncio.to_thread(_fetch)
        for row in rows:
            # Re-emit as GHOST
            await bus.publish(
                "killfeed.kill",
                {
                    "killer": row.get("attacker_name"),
                    "victim": row.get("victim_name"),
                    "weapon": row.get("weapon"),
                    "distance": row.get("distance"),
                    "location": row.get("location") or "Unknown",
                    "timestamp": datetime.utcnow().isoformat(),
                    "is_ghost": True,
                    "source": "ghost_replay",
                },
            )

        return {"status": "success", "replayed": len(rows)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# === SELFPLAY HARVEST_PROBE MODE ===


@app.post("/ops/selfplay")
async def ops_selfplay(body: dict | None = None):
    """Run selfplay diagnostics or Discord suite"""
    if body is None:
        body = {}
    try:
        mode = body.get("mode", "HARVEST_PROBE")
        run_id = str(uuid.uuid4())[:8]
        log.info(f"SELFPLAY BEGIN run_id={run_id} mode={mode}")

        if mode == "DISCORD_SUITE":
            if not _bot_ref:
                return {"status": "error", "message": "Bot not connected"}

            cog = _bot_ref.get_cog("SelfplayCog")
            if not cog:
                return {"status": "error", "message": "SelfplayCog not loaded"}

            # Use Casino channel by default or from body
            channel_id = int(body.get("channel_id", 1452554475909812366))

            # Fix cross-thread execution by scheduling on bot loop
            future = asyncio.run_coroutine_threadsafe(cog.trigger_suite(channel_id), _bot_ref.loop)
            success = await asyncio.wrap_future(future)

            return {
                "status": "triggered" if success else "failed",
                "run_id": run_id,
                "mode": mode,
                "channel_id": channel_id,
            }

        staging = Path("staging/ezstreet/dayzxb_missions/dayzOffline.chernarusplus").resolve()
        results = {"run_id": run_id, "mode": mode, "ts": datetime.utcnow().isoformat(), "probes": {}}

        # H1: Economy Pool Coupling - check Hatchback nominal
        try:
            types_xml = (staging / "db/types.xml").read_text()
            h1_pass = "<nominal>2</nominal>" in types_xml and 'name="Hatchback_02"' in types_xml
            results["probes"]["H1_economy_pool"] = {
                "pass": h1_pass,
                "evidence": "Hatchback_02 nominal=2" if h1_pass else "nominal not 2",
            }
        except Exception as e:
            results["probes"]["H1_economy_pool"] = {"pass": False, "evidence": str(e)}

        # H2: Events XML child tags (not attributes)
        try:
            events_xml = (staging / "db/events.xml").read_text()
            h2_pass = 'name="VehicleAdminHatchback02"' in events_xml and "<nominal>1</nominal>" in events_xml
            results["probes"]["H2_event_child_tags"] = {
                "pass": h2_pass,
                "evidence": "VehicleAdminHatchback02 with child tags" if h2_pass else "missing or attribute-only",
            }
        except Exception as e:
            results["probes"]["H2_event_child_tags"] = {"pass": False, "evidence": str(e)}

        # H3: Mission path verification
        try:
            mission_exists = staging.exists() and (staging / "cfggameplay.json").exists()
            results["probes"]["H3_mission_path"] = {
                "pass": mission_exists,
                "evidence": str(staging) if mission_exists else "path not found",
            }
        except Exception as e:
            results["probes"]["H3_mission_path"] = {"pass": False, "evidence": str(e)}

        # H4: Container sentinel (init.c should NOT exist)
        try:
            init_c = staging / "init.c"
            h4_pass = not init_c.exists()
            results["probes"]["H4_console_compliant"] = {
                "pass": h4_pass,
                "evidence": "init.c absent (console OK)" if h4_pass else "init.c exists (PC mode)",
            }
        except Exception as e:
            results["probes"]["H4_console_compliant"] = {"pass": False, "evidence": str(e)}

        # H5: Patch execution check
        try:
            manifest = Path("backend/patcher/v2/patches/manifest.json").resolve()
            if manifest.exists():
                import json

                m = json.loads(manifest.read_text())
                enabled = sum(1 for p in m.get("patches", []) if p.get("enabled"))
                h5_pass = enabled > 0
                results["probes"]["H5_patch_manifest"] = {"pass": h5_pass, "evidence": f"{enabled} patches enabled"}
            else:
                results["probes"]["H5_patch_manifest"] = {"pass": False, "evidence": "manifest not found"}
        except Exception as e:
            results["probes"]["H5_patch_manifest"] = {"pass": False, "evidence": str(e)}

        # Calculate overall
        all_pass = all(p.get("pass", False) for p in results["probes"].values())
        results["status"] = "PASS" if all_pass else "FAIL"

        # Write artifacts
        runs_dir = Path("logs/selfplay_runs").resolve()
        runs_dir.mkdir(parents=True, exist_ok=True)

        json_path = runs_dir / f"{run_id}.json"
        md_path = runs_dir / f"{run_id}.md"

        import json

        json_path.write_text(json.dumps(results, indent=2))

        md_content = f"""# SELFPLAY run_id={run_id} mode={mode}
    ## Status: {results["status"]}
    ## Timestamp: {results["ts"]}

    | Hypothesis | Result | Evidence |
    |------------|--------|----------|
    """
        for k, v in results["probes"].items():
            md_content += f"| {k} | {'✅ PASS' if v['pass'] else '❌ FAIL'} | {v['evidence']} |\n"

        md_path.write_text(md_content)

        log.info(f"SELFPLAY END run_id={run_id} status={results['status']}")

        return {"ok": True, "run_id": run_id, "mode": mode, "status": results["status"], "probes": results["probes"]}
    except Exception as e:
        log.error(f"OPS SELFPLAY ERROR: {e}")
        import traceback

        return {"status": "error", "message": str(e), "trace": traceback.format_exc()}


# === DISCORD CHANNEL INSPECTION API ===
# Reusable endpoints for reading Discord channels and messages


@app.get("/discord/channels/list")
async def discord_list_channels(category: str | None = None):
    """List all accessible Discord channels in the guild"""
    if not _bot_ref:
        return {"status": "error", "message": "Bot not connected"}

    guild = _bot_ref.get_guild(_bot_ref.settings.discord_guild_id)
    if not guild:
        return {"status": "error", "message": "Guild not found"}

    channels = []
    for ch in guild.channels:
        ch_data = {
            "id": ch.id,
            "name": ch.name,
            "type": str(ch.type),
            "category": ch.category.name if ch.category else None,
            "category_id": ch.category.id if ch.category else None,
        }
        if category and ch.category:
            if category.lower() not in ch.category.name.lower():
                continue
        channels.append(ch_data)

    return {"status": "ok", "guild": guild.name, "channels": channels, "count": len(channels)}


@app.get("/discord/channels/{channel_id}")
async def discord_get_channel(channel_id: int):
    """Get info about a specific Discord channel"""
    if not _bot_ref:
        return {"status": "error", "message": "Bot not connected"}

    channel = _bot_ref.get_channel(channel_id)
    if not channel:
        return {"status": "error", "message": f"Channel {channel_id} not found"}

    return {
        "status": "ok",
        "channel": {
            "id": channel.id,
            "name": channel.name,
            "type": str(channel.type),
            "category": channel.category.name if channel.category else None,
            "topic": getattr(channel, "topic", None),
            "created_at": channel.created_at.isoformat() if channel.created_at else None,
        },
    }


@app.get("/discord/channels/{channel_id}/messages")
async def discord_get_messages(channel_id: int, limit: int = 10):
    """Read recent messages from a Discord channel - reusable for live inspection"""
    if not _bot_ref:
        return {"status": "error", "message": "Bot not connected"}

    channel = _bot_ref.get_channel(channel_id)
    if not channel:
        return {"status": "error", "message": f"Channel {channel_id} not found"}

    # Ensure it's a text channel with message history
    if not hasattr(channel, "history"):
        return {"status": "error", "message": f"Channel {channel_id} does not support message history"}

    try:
        messages = []
        async for msg in channel.history(limit=min(limit, 50)):
            msg_data = {
                "id": msg.id,
                "author": msg.author.name,
                "author_id": msg.author.id,
                "content": msg.content[:500] if msg.content else "",
                "timestamp": msg.created_at.isoformat(),
                "embeds": len(msg.embeds),
                "attachments": len(msg.attachments),
                "reactions": [{"emoji": str(r.emoji), "count": r.count} for r in msg.reactions],
            }
            if msg.embeds:
                msg_data["embed_titles"] = [e.title for e in msg.embeds if e.title]
            messages.append(msg_data)

        return {
            "status": "ok",
            "channel_id": channel_id,
            "channel_name": channel.name,
            "messages": messages,
            "count": len(messages),
        }
    except Exception as e:
        log.error(f"Failed to read messages from {channel_id}: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/discord/channels/{channel_id}/send")
async def discord_send_message(channel_id: int, content: str):
    """Send a message to a Discord channel - for testing/automation"""
    if not _bot_ref:
        return {"status": "error", "message": "Bot not connected"}

    channel = _bot_ref.get_channel(channel_id)
    if not channel:
        return {"status": "error", "message": f"Channel {channel_id} not found"}

    if not hasattr(channel, "send"):
        return {"status": "error", "message": f"Channel {channel_id} does not support sending"}

    try:
        msg = await channel.send(content)
        return {"status": "ok", "message_id": msg.id, "sent": content[:100]}
    except Exception as e:
        log.error(f"Failed to send to {channel_id}: {e}")
        return {"status": "error", "message": str(e)}


# === KNOWN CHANNEL SHORTCUTS ===
KNOWN_CHANNELS = {
    "casino": 1452554475909812366,
    "killfeed": 1453504155388874906,
    "deathfeed": 1453504309634531490,
    "status": 1453978341076893868,
    "todo": 1454568932051783918,
    "admin": 1454365351365316713,
    "sandbox": 1454646232374055116,
    "deploy": 1454362669510561854,
}


@app.get("/discord/inspect/{channel_name}")
async def discord_inspect_named_channel(channel_name: str, limit: int = 10):
    """Inspect a known channel by name (casino, killfeed, todo, etc.)"""
    channel_id = KNOWN_CHANNELS.get(channel_name.lower())
    if not channel_id:
        return {
            "status": "error",
            "message": f"Unknown channel name: {channel_name}",
            "known_channels": list(KNOWN_CHANNELS.keys()),
        }
    return await discord_get_messages(channel_id, limit)
