from __future__ import annotations

import logging
import asyncio
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .tracking_db import Database as TrackingDB
from .tracker import PlayerTracker
from .name_generator import generate_codename
from .adm_log_parser import ADMLogParser

log = logging.getLogger("dayz-discord-ops.api")

app = FastAPI(title="DayZ Ops API")

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Import and include survival analytics router
from .survival_analytics import router as survival_router
app.include_router(survival_router)

# Import WebSocket endpoint for live logs
from .websocket_routes import websocket_logs_endpoint

@app.websocket("/ws/logs")
async def websocket_logs(websocket):
    """WebSocket endpoint for real-time log streaming"""
    await websocket_logs_endpoint(websocket)

# Background task control
_background_task_running = False
_background_task = None

@app.get("/health")
async def health():
    return {"status": "ok"}

# === Mission Management Endpoints ===
class MissionValidateRequest(BaseModel):
    path: str

class MissionScaleRequest(BaseModel):
    path: str
    nominal_mult: float
    min_mult: Optional[float] = None
    round_mode: str = "ceil"

@app.post("/mission/validate")
async def validate_mission_endpoint(req: MissionValidateRequest):
    """Validate DayZ mission structure and CE configuration"""
    try:
        from .mission_tools import validate_mission, Finding
        from pathlib import Path
        
        findings = validate_mission(Path(req.path))
        return {
            "status": "ok",
            "errors": [f.as_line() for f in findings if f.level == "ERROR"],
            "warnings": [f.as_line() for f in findings if f.level == "WARN"],
            "total": len(findings)
        }
    except Exception as e:
        log.error(f"Mission validation failed: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/mission/diagnose")
async def diagnose_mission_endpoint(req: MissionValidateRequest):
    """Run opinionated diagnostics on mission"""
    try:
        from .mission_tools import diagnose_mission
        from pathlib import Path
        
        notes = diagnose_mission(Path(req.path))
        return {
            "status": "ok",
            "notes": [{"title": n.title, "detail": n.detail} for n in notes]
        }
    except Exception as e:
        log.error(f"Mission diagnostics failed: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/mission/scale")
async def scale_mission_endpoint(req: MissionScaleRequest):
    """Scale nominal/min counts in types.xml"""
    try:
        from .mission_tools import scale_types_xml
        from pathlib import Path
        
        target_dir = Path(req.path)
        types_path = None
        for cand in [target_dir/'types.xml', target_dir/'db'/'types.xml']:
            if cand.exists():
                types_path = cand
                break
        
        if not types_path:
            return {"status": "error", "message": "Could not locate types.xml"}
        
        res = scale_types_xml(types_path, req.nominal_mult, req.min_mult, req.round_mode)
        return {
            "status": "ok",
            "touched": res.touched,
            "changed": res.changed,
            "path": str(types_path)
        }
    except Exception as e:
        log.error(f"Mission scaling failed: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/server/status")
async def get_server_status_endpoint():
    """High-fidelity merger of Nitrado (Account) and A2S (Live UDP) state."""
    from .config import load_settings
    from .nitrado_api import NitradoAPIClient
    
    settings = load_settings()
    service_id = settings.nitrado_service_id
    
    # Truth 1: Nitrado Account/Instance state
    nit_data = {"status": "unknown"}
    if settings.nitrado_token and service_id:
        try:
            client = NitradoAPIClient(settings.nitrado_token)
            details = client.get_gameserver_details(service_id)
            if details.get("status") == "success":
                nit_data = details.get("data", {}).get("gameserver", {})
        except Exception as e:
            log.error(f"Nitrado fetch failed: {e}")

    # Truth 2: A2S Live Query state (The "Universal Truth")
    a2s_data = {}
    if _bot_ref and hasattr(_bot_ref, 'last_a2s'):
        a2s_data = _bot_ref.last_a2s or {}

    return {
        "status": nit_data.get("status", "offline"),
        "data": {
            **nit_data,
            "query": {
                **nit_data.get("query", {}),
                "player_current": a2s_data.get("players", nit_data.get("query", {}).get("player_current", 0)),
                "player_max": a2s_data.get("max_players", nit_data.get("query", {}).get("player_max", 60)),
                "server_version": a2s_data.get("version", nit_data.get("query", {}).get("server_version", "1.28"))
            },
            "last_updated": datetime.now().isoformat()
        }
    }

@app.get("/bot/status")
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
        "extensions": len(_bot_ref.extensions)
    }

@app.get("/config")
async def get_sanitized_config():
    """Expose dynamic provenance and configuration."""
    from .config import load_settings
    settings = load_settings()
    
    # A2S state for versioning if available
    a2s_data = _bot_ref.last_a2s if _bot_ref else {}
    
    return {
        "org_id": settings.org_id,
        "server_name": settings.server_name,
        "platform": settings.platform.upper() if settings.platform else "XBOX",
        "region": "US-LA", # Dynamic region detection could be added
        "status": "ONLINE",
        "version": a2s_data.get("version", "1.28-SIGMA"),
        "patches_src_dir": settings.patches_src_dir,
        "mission_path": settings.mission_path,
        "vanilla_path": settings.vanilla_path
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

class SelfplayTriggerRequest(BaseModel):
    mode: str = "full_demo"
    count: int = 5

@app.post("/trigger/selfplay")
async def trigger_selfplay(req: SelfplayTriggerRequest):
    """Trigger the Discord bot's selfplay driver for self-testing."""
    import json
    from pathlib import Path
    from datetime import datetime
    
    trigger_path = Path("state/selfplay_trigger.json")
    trigger_path.parent.mkdir(parents=True, exist_ok=True)
    
    import subprocess
    
    cmd = ["python3", "bot/scripts/selfplay_driver.py"] # This might be wrong path, verifying... actually the driver is inside bot.
    # The TRIGGER is via file watch. The API just writes the file.
    
    trigger_path = Path("state/selfplay_trigger.json")
    with open(trigger_path, "w") as f:
        json.dump(req.dict(), f)
    
    log.info(f"Selfplay trigger written: {req.mode} x{req.count}")
    return {"status": "triggered", "mode": req.mode, "count": req.count}

@app.get("/security/scan")
async def security_scan():
    """Run security check and return results."""
    import subprocess
    import json
    
    try:
        # Execute the security script
        result = subprocess.run(
            ["python3", "bot/scripts/run_security_check.py", "dupe"], 
            capture_output=True, 
            text=True,
            check=False
        )
        
        if result.returncode != 0:
             return {"status": "error", "error": result.stderr}
             
        # Parse the output
        try:
            data = json.loads(result.stdout)
            return data
        except json.JSONDecodeError:
            return {"status": "error", "error": "Invalid JSON output", "raw": result.stdout}
            
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Global reference to bot instance, injected by bot.py
_bot_ref = None

# --- Protocol SIGMA: Log Verification ---

@app.get("/logs/probe")
async def probe_logs():
    """SIGMA-1: Connectivity Check"""
    if not _bot_ref: return {"status": "error", "message": "Bot instance not linked"}
    cog = _bot_ref.get_cog("LogIntelligence")
    if not cog: return {"status": "error", "message": "LogIntelligence offline"}
    return await cog.probe()

@app.post("/logs/sync")
async def sync_logs_manual():
    """SIGMA-2: Force Ingestion"""
    if not _bot_ref: return {"status": "error", "message": "Bot instance not linked"}
    cog = _bot_ref.get_cog("LogIntelligence")
    if not cog: return {"status": "error", "message": "LogIntelligence offline"}
    return await cog.ingest_once()

@app.get("/logs")
async def get_logs_sigma(limit: int = 50):
    """SIGMA-3: Serving"""
    if not _bot_ref: return {"status": "error", "message": "Bot instance not linked"}
    cog = _bot_ref.get_cog("LogIntelligence")
    if not cog: return {"status": "error", "message": "LogIntelligence offline"}
    return {"events": cog.get_recent_events(limit=limit)}
    
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
    logs = client.get_logs_list(service_id)
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
    
    content = client.download_file(service_id, req.path)
    if content is None:
         return {"error": "Failed to download log from Nitrado"}
    return {"content": content}

class PlayerActionRequest(BaseModel):
    gamertag: str

@app.get("/players")
async def get_players():
    """Get list of online players from Nitrado API (Xbox compatible)"""
    from .config import load_settings
    from .nitrado_api import NitradoAPIClient
    
    settings = load_settings()
    service_id = 18302446
    
    if not settings.nitrado_token:
        return {"players": []}
    
    try:
        client = NitradoAPIClient(settings.nitrado_token)
        details = client.get_gameserver_details(service_id)
        
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
                formatted_players.append({
                    "gamertag": player.get("name", "Unknown"),
                    "status": "online",
                    "last_seen": None,  # Real-time data
                    "score": player.get("score", 0),
                    "duration": player.get("duration", 0)
                })
            
            return {
                "players": formatted_players,
                "player_count": player_current,
                "max_players": player_max
            }
    except Exception as e:
        log.error(f"Failed to fetch players from Nitrado: {e}")
    
    return {"players": [], "player_count": 0, "max_players": 0}

@app.post("/players/kick")
async def kick_player(req: PlayerActionRequest):
    """Kick endpoint disabled (RCON removed)."""
    return {"status": "error", "message": "RCON disabled; kick not available"}

@app.get("/economy")
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
    import os
    from .config import load_settings
    from .ftp_client import FTPClient
    
    # Try local mission path from config
    settings = load_settings()
    mission_path = Path(settings.mission_path)
    db_path = mission_path / "db"
    try:
        if db_path.exists():
            files = [f for f in db_path.iterdir() if f.is_file() and f.name.endswith('.xml')]
            return {"files": sorted([f.name for f in files]), "source": "local"}
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
        files = [f['name'] for f in files_raw if f['name'].endswith('.xml')]
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
    if '..' in filename or filename.startswith('/'):
        return {"error": "Invalid filename"}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
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

    if '..' in filename or filename.startswith('/'):
        return {"error": "Invalid filename"}

    try:
        # Create backup if requested
        if req.backup and os.path.exists(file_path):
             shutil.copy2(file_path, backup_path)
             
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(req.content)
            
        return {"status": "success", "message": f"Updated {filename}"}
    except Exception as e:
        log.error(f"Failed to update file {filename}: {e}")
        return {"status": "error", "message": str(e)}

# Keep existing economy endpoints for backward compat / script triggering
@app.get("/economy/config")
async def get_economy_settings():
    """Get economy configuration from JSON"""
    import json
    import os
    from pathlib import Path
    
    # Config is now in backend_data volume, separated from game files
    if os.path.exists("/app/backend_data"):
        base_path = Path("/app/backend_data")
    else:
        # Local dev fallback
        repo_root = Path(__file__).parent.parent.parent
        base_path = repo_root / "backend_data"
        
    config_path = base_path / "EZStreet_ServerConfig.json"
    
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        log.error(f"Failed to read economy config: {e}")
        return {"error": str(e), "economy": {}}

class EconomyUpdateRequest(BaseModel):
    loot_multiplier: float
    lifetime_multiplier: float
    zombie_max: int
    animal_max: int

@app.post("/economy/config")
async def update_economy_settings(req: EconomyUpdateRequest):
    """Update economy configuration and run apply script"""
    import json
    import subprocess
    import shutil
    
    # Determine paths based on environment
    import os
    from pathlib import Path
    
    if os.path.exists("/app/backend_data"):
        base_path = Path("/app/backend_data")
    else:
        # Local dev fallback: assumed to be run from repo root or src
        # Try to find dayz_discord_ops_repo/backend_data
        # We are likely in src/dayz_discord_ops/api.py
        current_dir = Path(__file__).parent
        # Go up to repo root
        repo_root = current_dir.parent.parent
        base_path = repo_root / "backend_data"
        
    config_path = base_path / "EZStreet_ServerConfig.json"
    script_path = base_path / "configeconomy.py"
    
    # Read existing to preserve other fields like "organization"
    try:
        with open(config_path, 'r') as f:
            current_data = json.load(f)
    except:
        current_data = {"organization": "EZStreet", "version": "1.0", "economy": {}}

    current_data["economy"] = req.dict()

    try:
        with open(config_path, 'w') as f:
            json.dump(current_data, f, indent=2)
            
        # Run the script
        # This script applies the config to the /app/missions volume or local equivalent
        cmd = ["python3", str(script_path)]
        log.info(f"Running hook script: {cmd}")
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
             return {"status": "warning", "message": "Config saved but script failed", "stderr": result.stderr}

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
        conn = get_db_connection(settings)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, player_count, max_players 
            FROM server_stats 
            WHERE timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY timestamp ASC
        """)
        for row in cursor.fetchall():
            stats.append({
                "timestamp": row[0].isoformat() if row[0] else None,
                "player_count": row[1],
                "max_players": row[2]
            })
        cursor.close()
        conn.close()
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

# Initialize simple singleton for the tracker DB
# In a real app, use dependency injection or a proper singleton pattern
_tracking_db = TrackingDB("player_intel.db")

class AliasRequest(BaseModel):
    steam_id: str
    fake_name: str

@app.get("/intelligence/players")
async def get_intelligence_players(scan: bool = False):
    """
    Get all tracked players.
    If scan=True, performs a live scan first (not available on console).
    """
    from .config import load_settings
    settings = load_settings()
    
    # Lazy init tracker with settings
    # For now, we reuse the same DB instance
    tracker = PlayerTracker(
        _tracking_db, 
        settings.dayz_host, 
        0,
        "",
        mock_mode=False # Placeholder for future non-RCON scan
    )
    
    if scan:
        try:
           tracker.scan_and_update()
        except Exception as e:
           log.error(f"Scan failed: {e}")
           # Continue to return cache
           
    players = _tracking_db.get_all_players()
    return {"players": players}

@app.post("/intelligence/scan_logs")
async def scan_logs_for_intelligence():
    """
    Scan Nitrado ADM logs for player activity (console-friendly alternative to RCON).
    Downloads latest log, parses events, updates tracking DB.
    """
    from .config import load_settings
    from .nitrado_api import NitradoAPIClient
    
    settings = load_settings()
    service_id = 18302446
    
    if not settings.nitrado_token:
        return {"status": "error", "message": "Nitrado API token not configured"}
    
    client = NitradoAPIClient(settings.nitrado_token)
    logs = client.get_logs_list(service_id)
    
    if not logs:
        return {"status": "error", "message": "No logs found"}
    
    # Get the most recent ADM log
    adm_logs = [l for l in logs if '.ADM' in l.upper()]
    if not adm_logs:
        return {"status": "error", "message": "No ADM logs found"}
    
    latest_log = sorted(adm_logs)[-1]
    log_content = client.download_file(service_id, latest_log)
    
    if not log_content:
        return {"status": "error", "message": "Failed to download log"}
    
    # Parse events
    parser = ADMLogParser()
    events = parser.parse_log_content(log_content)
    
    # Update tracking DB
    players_updated = 0
    for event in events:
        if event['event_type'] == 'connect':
            _tracking_db.update_player(event['player_id'], event['gamertag'])
            _tracking_db.log_session(event['player_id'], f"Server_{service_id}")
            
            # Auto-assign alias if needed
            player_record = _tracking_db.get_player(event['player_id'])
            if player_record and not player_record['fake_name']:
                new_alias = generate_codename()
                _tracking_db.set_alias(event['player_id'], new_alias)
            
            players_updated += 1
    
    return {
        "status": "success",
        "log_file": latest_log,
        "events_parsed": len(events),
        "players_updated": players_updated
    }

@app.post("/intelligence/alias")
async def set_player_alias(req: AliasRequest):
    _tracking_db.set_alias(req.steam_id, req.fake_name)
    return {"status": "success", "message": f"Alias set for {req.steam_id}"}

@app.get("/killfeed")
async def get_killfeed(limit: int = 50):
    from .config import load_settings
    settings = load_settings()
    conn = get_db_connection(settings)
    if not conn:
        return {"kills": []}
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM combat_logs ORDER BY timestamp DESC LIMIT %s", 
                (limit,)
            )
            rows = cursor.fetchall()
            return {"kills": rows}
    except Exception as e:
        log.error(f"Failed to fetch killfeed: {e}")
        return {"kills": []}
    finally:
        conn.close()

# --- Economy Intelligence ---

@app.get("/economy/intelligence/clusters")
async def get_economy_clusters():
    from .economy_intelligence import EconomyIntelligence
    from pathlib import Path
    
    from .config import load_settings
    settings = load_settings()
    mission_path = Path(settings.mission_path)
    # Path to types.xml in mission volume
    path = mission_path / "db" / "types.xml"
    
    intel = EconomyIntelligence(path)
    return intel.get_smart_clusters()

@app.get("/economy/intelligence/validate")
async def validate_economy():
    from .economy_intelligence import EconomyIntelligence
    from pathlib import Path
    
    path = Path("/app/missions/dayzOffline.chernarusplus/db/types.xml")
    if not path.exists():
         path = Path(__file__).parent.parent.parent / "dayzxb_missions" / "dayzOffline.chernarusplus" / "db" / "types.xml"
    
    intel = EconomyIntelligence(path)
    return {"warnings": intel.validate_logic()}



# Global bot reference for status access
_bot_ref = None

@app.get("/bot/status")
async def get_bot_status():
    if not _bot_ref:
        return {"status": "inactive", "message": "API running standalone"}
    
    guild = _bot_ref.get_guild(_bot_ref.settings.discord_guild_id)
    return {
        "status": "online" if _bot_ref.is_ready() else "connecting",
        "name": str(_bot_ref.user),
        "guild": guild.name if guild else "Unknown",
        "guild_id": _bot_ref.settings.discord_guild_id,
        "latency": f"{round(_bot_ref.latency * 1000)}ms"
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
        for r in data['results']:
            simple_results.append({
                "id": r.channel_id,
                "name": r.channel_name,
                "type": r.channel_type,
                "category": r.category,
                "matched_feature": r.matched_feature,
                "suggestions": r.suggestions
            })
        data['results'] = simple_results
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
    # Looking at bot.py, it updates prometheus metrics.
    # We can check A2S_UP value or similar if we imported it, 
    # but accessing _bot_ref state is better if possible.
    # bot.py doesn't seem to store `last_info` publicly on self, 
    # but `stat_tick` updates it.
    
    # Let's return a simple status based on A2S_UP metric which is imported in bot.py
    # Actually, we can just import the metrics here too.
    from .metrics import A2S_UP, A2S_PLAYERS
    
    is_up = A2S_UP._value.get() == 1.0
    players = A2S_PLAYERS._value.get()
    
    return {
        "status": "online" if is_up else "offline",
        "players": players,
        "message": "Cached status from bot"
    }

@app.get("/bot/logs")
async def get_bot_logs(limit: int = 50):
    from .config import load_settings
    from .database import get_db_connection
    
    settings = load_settings()
    logs = []
    try:
        conn = get_db_connection(settings)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, type, message, severity FROM activity_logs ORDER BY timestamp DESC LIMIT %s", (limit,))
        for row in cursor.fetchall():
            logs.append({
                "timestamp": row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp']) if row['timestamp'] else None,
                "type": row['type'],
                "message": row['message'],
                "severity": row['severity']
            })
        cursor.close()
        conn.close()
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
                "ZombieMaxCount": globals_data.get('ZombieMaxCount', 1000),
                "AnimalMaxCount": globals_data.get('AnimalMaxCount', 200),
                "LootDamageMin": globals_data.get('LootDamageMin', 0.0),
                "LootDamageMax": globals_data.get('LootDamageMax', 0.0)
            }
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
        
        if 'ZombieMaxCount' in req:
            updates['ZombieMaxCount'] = int(req['ZombieMaxCount'])
        if 'AnimalMaxCount' in req:
            updates['AnimalMaxCount'] = int(req['AnimalMaxCount'])
        if 'LootDamageMin' in req:
            updates['LootDamageMin'] = float(req['LootDamageMin'])
        if 'LootDamageMax' in req:
            updates['LootDamageMax'] = float(req['LootDamageMax'])
        
        success = manager.update_globals(updates)
        
        if success:
            uploaded = manager.upload_to_server(
                str(manager.globals_xml), 
                '/dayzxb_missions/dayzOffline.chernarusplus/db/globals.xml'
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
                '/dayzxb_missions/dayzOffline.chernarusplus/cfggameplay.json'
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
                '/dayzxb_missions/dayzOffline.chernarusplus/cfggameplay.json'
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
                '/dayzxb_missions/dayzOffline.chernarusplus/cfgweather.xml'
            )
            return {"status": "success", "message": "Weather config updated", "uploaded": uploaded}
        else:
            return {"status": "error", "message": "Failed to update weather config"}
    except Exception as e:
        log.error(f"Failed to update weather config: {e}")
        return {"status": "error", "message": str(e)}

# Background intelligence scanning

async def intelligence_background_task():
    """Background task to periodically scan for players and update intelligence DB"""
    from .config import load_settings
    
    log.info("Starting background intelligence scanner...")
    settings = load_settings()
    
    tracker = PlayerTracker(
        _tracking_db,
        settings.dayz_host,
        0,
        "",
        mock_mode=False
    )
    
    while _background_task_running:
        try:
            log.info("Running intelligence scan...")
            tracker.scan_and_update()
            log.info("Intelligence scan complete")
        except Exception as e:
            log.error(f"Intelligence scan failed: {e}")
        
        # Wait 5 minutes before next scan
        await asyncio.sleep(300)

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
    log.info("Starting API server on %s:%s (Proxy Headers ENABLED)", host, port)
    uvicorn.run(
        app, 
        host=host, 
        port=port, 
        log_level="info",
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
