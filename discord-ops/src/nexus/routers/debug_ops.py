
from fastapi import APIRouter
from pydantic import BaseModel
import logging
from datetime import datetime
from src.mildlyawesome.events import get_bus
from src.mildlyawesome.log_streamer import get_streamer
from src.mildlyawesome.social_streamer import SocialEvent, get_social_streamer

router = APIRouter(tags=["Debug Ops"])
log = logging.getLogger("mildlyawesome.api.debug")

# --- Models ---
class PatchAnnouncementRequest(BaseModel):
    title: str
    version: str
    description: str = ""
    changes: list[str] = []

# --- Endpoints ---

@router.post("/debug/mock_social")
async def mock_social(user: str = "TestUser", message: str = "Hello from AIS!"):
    streamer = get_social_streamer()
    event = SocialEvent(timestamp=datetime.utcnow().isoformat(), source="debug", user=user, message=message)
    await streamer.broadcast(event)
    return {"status": "dispatched"}

@router.post("/debug/emit_event")
async def debug_emit_event(event_type: str, payload: dict):
    """Inject an event directly into the High-Fidelity Event Fabric."""
    bus = get_bus()
    await bus.publish(event_type, payload)
    await bus.publish(event_type, payload)
    return {"status": "published", "type": event_type, "payload": payload}

@router.post("/debug/inject_log")
async def debug_inject_log(line: str, source: str = "nitrado"):
    """Inject a raw log line into LogStreamer to test parsing and correlation."""
    streamer = get_streamer()
    
    # Simulate parser
    event = streamer._parse_generic_log_line(line, source, "adm" if "ADM" in line else "rpt")

    if event:
        await streamer._broadcast_event(event)
        return {"status": "injected", "cid": event.correlation_id, "parsed": event.to_json()}
    return {"status": "ignored", "reason": "parser returned None"}

@router.post("/ops/announce_patch")
async def announce_patch_endpoint(req: PatchAnnouncementRequest):
    """Trigger a manual patch announcement to Discord."""
    bus = get_bus()
    payload = req.dict()
    payload["timestamp"] = datetime.utcnow().isoformat()
    await bus.publish("patch.applied", payload)
    return {"status": "published", "target": "changelog"}

@router.get("/security/scan")
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

@router.post("/simulation/trigger")
async def trigger_simulation(mode: str = "full_demo", count: int = 3):
    """Trigger SelfPlayDriver simulation via the bot."""
    from src.mildlyawesome.globals import get_bot
    import asyncio
    bot = get_bot()
    if not bot: return {"status": "error", "message": "Bot not connected"}
    cog = bot.get_cog("SelfPlayDriver")
    if not cog: return {"status": "error", "message": "SelfPlayDriver cog not loaded"}
    try:
        instruction = {"mode": mode, "count": count}
        asyncio.run_coroutine_threadsafe(cog.execute_instruction(instruction), bot.loop)
        return {"status": "success", "message": f"Simulation started: {mode}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/ops/backup")
async def trigger_backup():
    """Trigger the server backup script in the background."""
    import subprocess
    from pathlib import Path
    script_path = Path(__file__).parent.parent / "scripts" / "backup_server.py"
    try:
        subprocess.Popen(["python3", str(script_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"status": "success", "message": "Backup job dispatched"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/test/killfeed")
async def test_killfeed(payload: dict):
    """Trigger test killfeed event via EventBus"""
    from src.mildlyawesome.globals import get_bot
    bot = get_bot()
    if bot and hasattr(bot, "event_bus"):
        await bot.event_bus.publish("killfeed.kill", payload)
        return {"status": "ok", "payload": payload}
    return {"status": "error", "message": "Bot/EventBus not ready"}

@router.post("/test/ghost_replay")
async def test_ghost_replay(limit: int = 5):
    """Fetch historical kills and replay them as 'GHOST' events for verification."""
    from src.mildlyawesome.globals import get_bot
    from src.mildlyawesome.config import load_settings
    from src.mildlyawesome.database import get_db_connection
    import asyncio
    bot = get_bot()
    if not bot: return {"status": "error", "message": "Bot not connected"}
    settings = load_settings()
    try:
        conn = await get_db_connection(settings)
        if not conn: return {"status": "error", "message": "DB not connected"}
        def _fetch():
            with conn.cursor() as cursor:
                cursor.execute("SELECT attacker_name, victim_name, weapon, distance, location FROM combat_logs ORDER BY timestamp DESC LIMIT %s", (limit,))
                return cursor.fetchall()
        rows = await asyncio.to_thread(_fetch)
        for row in rows:
            await bot.event_bus.publish("killfeed.kill", {
                "killer": row.get("attacker_name"),
                "victim": row.get("victim_name"),
                "weapon": row.get("weapon"),
                "distance": row.get("distance"),
                "location": row.get("location") or "Unknown",
                "is_ghost": True,
                "timestamp": datetime.utcnow().isoformat()
            })
        conn.close()
        return {"status": "success", "replayed": len(rows)}
    except Exception as e:
        return {"status": "error", "message": str(e)}
