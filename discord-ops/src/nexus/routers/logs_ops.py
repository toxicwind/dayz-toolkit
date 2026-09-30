
from fastapi import APIRouter, WebSocket
from pydantic import BaseModel
import logging
from dataclasses import asdict
from src.mildlyawesome.globals import get_bot
from src.mildlyawesome.log_streamer import get_streamer
from src.mildlyawesome.config import load_settings
from src.mildlyawesome.ftp_client import FTPClient
from src.mildlyawesome.nitrado_api import NitradoAPIClient
from src.mildlyawesome.bus import get_bus

router = APIRouter(tags=["Log Intelligence"])
log = logging.getLogger("mildlyawesome.api.logs")

# --- Models ---
class LogReadRequest(BaseModel):
    path: str

# --- Endpoints ---

@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """Real-time log streaming via WebSocket with EventBus integration."""
    await websocket.accept()
    bus = get_bus()
    await bus.connect()
    
    log.info(f"🔌 WebSocket log subscriber connected: {websocket.client}")

    async def log_callback(data):
        try:
            await websocket.send_json(data)
        except Exception:
            pass

    await bus.subscribe("logs.*", log_callback)
    
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        log.info(f"🔌 WebSocket log subscriber disconnected: {websocket.client}")

@router.get("/logs/probe")
async def probe_logs():
    """SIGMA-1: Connectivity Check"""
    bot = get_bot()
    if not bot:
        return {"status": "error", "message": "Bot instance not linked"}
    cog = bot.get_cog("LogIntelligence")
    if cog:
        return await cog.probe()
    
    streamer = get_streamer()
    return {
        "status": "ok",
        "source": "log_streamer",
        "buffer_size": len(streamer.log_buffer),
        "clients": len(streamer.clients),
    }

@router.post("/logs/sync")
async def sync_logs_manual():
    """SIGMA-2: Force Ingestion"""
    bot = get_bot()
    if not bot:
        return {"status": "error", "message": "Bot instance not linked"}
    cog = bot.get_cog("LogIntelligence")
    if cog:
        return await cog.ingest_once()
    
    streamer = get_streamer()
    return {
        "status": "ok",
        "source": "log_streamer",
        "message": "Log streamer is continuously polling FTP/Nitrado",
        "buffer_size": len(streamer.log_buffer),
    }

@router.get("/logs")
async def get_logs_sigma(limit: int = 50):
    """SIGMA-3: Serving - returns recent log events"""
    bot = get_bot()
    if bot:
        cog = bot.get_cog("LogIntelligence")
        if cog:
            return {"events": cog.get_recent_events(limit=limit)}

    streamer = get_streamer()
    events = list(streamer.log_buffer)[-limit:]
    return {"events": [asdict(e) for e in events], "source": "log_streamer", "total_buffered": len(streamer.log_buffer)}

@router.post("/logs/content")
async def read_log_content(req: LogReadRequest):
    settings = load_settings()
    if not settings.ftp_host:
        return {"error": "FTP not configured"}

    client = FTPClient(settings.ftp_host, settings.ftp_port, settings.ftp_user, settings.ftp_password)
    try:
        client.connect()
        content = client.read_file(req.path)
        if content is None:
            return {"error": "Failed to read file"}
        return {"content": content}
    finally:
        client._close()

@router.get("/nitrado/logs")
async def list_nitrado_logs():
    settings = load_settings()
    if not settings.nitrado_token:
        return {"error": "Nitrado API token not configured"}

    client = NitradoAPIClient(settings.nitrado_token)
    service_id = settings.nitrado_service_id
    if not service_id:
        return {"error": "Nitrado Service ID not configured"}

    logs = await client.get_logs_list(service_id)
    return {"files": [{"name": f, "path": f} for f in logs]}

@router.post("/nitrado/logs/content")
async def read_nitrado_log_content(req: LogReadRequest):
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
