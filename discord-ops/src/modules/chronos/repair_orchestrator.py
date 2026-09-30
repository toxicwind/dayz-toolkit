import asyncio
import logging
from src.mildlyawesome.events import get_bus
from .service import ChronosService

log = logging.getLogger("mildlyawesome.modules.chronos.repair")

class ReactiveRepair:
    def __init__(self):
        self.bus = get_bus()
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        log.info("Chronos Reactive Repair Engine ONLINE")
        self.bus.subscribe("error", self.on_error)
        self.bus.subscribe("patch.failed", self.on_patch_failure)

    async def on_error(self, payload: dict):
        """React to system errors."""
        msg = payload.get("message", "Unknown error")
        log.warning(f"Chronos intercepting error: {msg}")
        
        # Trigger exhumation if the error looks like a config issue
        if any(kw in msg.lower() for kw in ["keyerror", "config", "settings", "missing"]):
            log.info("Detected potential config instability. Launching Exhumation...")
            await ChronosService.run_chronos_audit()

    async def on_patch_failure(self, payload: dict):
        """React to patch failures."""
        target = payload.get("target", "unknown")
        log.warning(f"Chronos intercepting patch failure on {target}")
        
        # Deep exhumation focused on the target area
        log.info(f"Performing targeted entropy scan for {target}")
        emap = await ChronosService.entropy_scan()
        # Logic to find hotspots near target
        hotspots = [k for k, v in emap.items() if v["entropy"] > 5.0]
        if hotspots:
            log.info(f"Identified {len(hotspots)} hotspots for {target}: {hotspots}")
            # Trigger targeted exhumation or recovery if needed
            
    async def run_autonomous_loop(self):
        """Main autonomous self-repair loop."""
        log.info("Chronos Autonomous Self-Repair Loop STARTED")
        while self._running:
            try:
                # 1. Passive Entropy Check
                emap = await ChronosService.entropy_scan()
                high_entropy = [k for k, v in emap["map"].items() if v["entropy"] > 10.0]
                
                if high_entropy:
                    log.warning(f"High Entropy detected in: {high_entropy}. Commencing predictive exhumation.")
                    await ChronosService.run_chronos_audit()
                
                # 2. Sync with Hub Registry
                # (Multi-agent awareness could happen here)
                
                await asyncio.sleep(300) # Run every 5 minutes
            except Exception as e:
                log.error(f"Autonomous loop error: {e}")
                await asyncio.sleep(60)

_orchestrator: ReactiveRepair | None = None

async def start_repair_loop():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ReactiveRepair()
        await _orchestrator.start()
        asyncio.create_task(_orchestrator.run_autonomous_loop())
