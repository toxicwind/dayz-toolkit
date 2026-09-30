
from fastapi import APIRouter
from pydantic import BaseModel
import logging
from datetime import datetime
from src.mildlyawesome.globals import get_bot
from src.mildlyawesome.config import load_settings
from src.mildlyawesome.nitrado_api import NitradoAPIClient

router = APIRouter(tags=["Server Ops"])
log = logging.getLogger("mildlyawesome.api.server")

# --- Models ---
class BanRequest(BaseModel):
    gamertag: str

# --- Endpoints ---

@router.get("/server/status")
async def get_server_status_endpoint():
    """High-fidelity merger of Nitrado (Account) and A2S (Live UDP) state."""
    bot = get_bot()
    if not bot:
        return {"status": "offline", "data": {}}

    cog = bot.get_cog("StatusCog")
    if not cog:
        return {"status": "error", "message": "Status module not loaded"}

    status = cog.service.get_cached_status()
    if not status:
        status, _, _ = await cog.service.update()

    from src.mildlyawesome.health_monitor import get_monitor
    monitor = get_monitor()
    health_summary = monitor.get_health_summary()

    return {
        "status": status.status,
        "data": {
            "status": status.status,
            "ip": bot.settings.dayz_host or "85.190.152.232",
            "port": bot.settings.dayz_query_port or "2302",
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

@router.get("/backend/status")
async def get_bot_status():
    """Discord Bot operational telemetry."""
    bot = get_bot()
    if not bot:
        return {"status": "offline", "guild": "N/A", "latency": "N/A"}

    latency_ms = round(bot.latency * 1000) if bot.latency else 0
    guild_name = "Unknown"
    if bot.settings.discord_guild_id:
        guild = bot.get_guild(bot.settings.discord_guild_id)
        if guild:
            guild_name = guild.name
    elif bot.guilds:
        guild_name = bot.guilds[0].name

    return {
        "status": "online" if not bot.is_closed() else "offline",
        "guild": guild_name,
        "latency": f"{latency_ms}ms",
        "uptime": getattr(bot, "uptime_str", "N/A"),
        "extensions": len(bot.extensions),
    }

@router.get("/config")
async def get_sanitized_config():
    """Expose dynamic provenance and configuration."""
    settings = load_settings()
    version = "1.28-SIGMA"
    region = "UNKNOWN"
    
    bot = get_bot()
    if bot:
        cog = bot.get_cog("StatusCog")
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

@router.post("/server/restart")
async def restart_server_endpoint():
    settings = load_settings()
    service_id = settings.nitrado_service_id
    if not service_id:
        return {"status": "error", "message": "Nitrado Service ID not configured"}

    client = NitradoAPIClient(settings.nitrado_token or "")
    res = client.restart_server(service_id)
    return res

@router.post("/server/stop")
async def stop_server_endpoint():
    settings = load_settings()
    service_id = settings.nitrado_service_id
    if not service_id:
        return {"status": "error", "message": "Nitrado Service ID not configured"}

    client = NitradoAPIClient(settings.nitrado_token or "")
    res = client.stop_server(service_id)
    return res

@router.post("/server/ban")
async def ban_player_endpoint(req: BanRequest):
    settings = load_settings()
    service_id = settings.nitrado_service_id
    if not service_id:
        return {"status": "error", "message": "Nitrado Service ID not configured"}

    client = NitradoAPIClient(settings.nitrado_token or "")
    res = client.ban_player(service_id, req.gamertag)
    return res

@router.get("/players")
async def get_players():
    """Get list of online players from Nitrado API (Xbox compatible)"""
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
            players_list = query.get("players", [])
            player_current = query.get("player_current", 0)
            player_max = query.get("player_max", 0)

            formatted_players = []
            for player in players_list:
                formatted_players.append(
                    {
                        "gamertag": player.get("name", "Unknown"),
                        "status": "online",
                        "last_seen": None,
                        "score": player.get("score", 0),
                        "duration": player.get("duration", 0),
                    }
                )

            return {"players": formatted_players, "player_count": player_current, "max_players": player_max}
    except Exception as e:
        log.error(f"Failed to fetch players from Nitrado: {e}")

    return {"players": [], "player_count": 0, "max_players": 0}

@router.get("/health")
async def health():
    return {"status": "ok"}
