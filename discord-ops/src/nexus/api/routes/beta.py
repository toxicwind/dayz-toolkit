from fastapi import APIRouter, Request
import logging

log = logging.getLogger(__name__)
router = APIRouter()

@router.post("/commands")
async def execute_beta_command(request: Request):
    data = await request.json()
    command = data.get("command")
    
    if command == "antigravity.startDemoMode":
        from src.mildlyawesome.core.bus import bus
        log.info("🚀 API: Triggering Full Live Demo Mode via EventBus...")
        # Publish event for cogs to pick up
        await bus.publish("demo.mode.start", {"triggered_by": "api"})
        return {"status": "triggered", "command": command}
        
    return {"status": "unknown", "command": command}
