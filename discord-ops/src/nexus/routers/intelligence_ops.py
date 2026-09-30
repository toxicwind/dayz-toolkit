
from fastapi import APIRouter
import logging
from src.mildlyawesome.globals import get_bot
from src.mildlyawesome.metrics import A2S_PLAYERS, A2S_UP
from src.mildlyawesome.events import get_bus

router = APIRouter(tags=["Intelligence & Webhooks"])
log = logging.getLogger("mildlyawesome.api.intelligence")

@router.get("/intelligence/emergent")
async def get_emergent_intelligence():
    """Get emergent feature metrics (Heatmaps, Economy, Anomalies)."""
    bot = get_bot()
    if not bot:
        return {"status": "error", "message": "Bot instance not linked"}

    cog = bot.get_cog("LogIntelligence")
    if not cog:
        return {"status": "error", "message": "LogIntelligence system offline"}

    return cog.intel_engine.get_emergent_intelligence()

@router.get("/a2s/status")
async def get_a2s_status():
    """Cached status from backend metrics."""
    is_up = A2S_UP._value.get() == 1.0
    players = A2S_PLAYERS._value.get()

    return {
        "status": "online" if is_up else "offline",
        "players": players,
        "message": "Cached status from backend",
    }

@router.post("/api/webhooks/vpp")
async def vpp_webhook(payload: dict):
    """Receives events from VPPAdminTools Webhook."""
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
