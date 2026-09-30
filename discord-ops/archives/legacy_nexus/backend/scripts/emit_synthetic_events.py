import asyncio
import logging
from datetime import datetime

import aiohttp

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("synthetic_events")

BASE_URL = "http://localhost:19101"


async def emit_events():
    async with aiohttp.ClientSession() as session:
        log.info("🚀 Emitting synthetic events via API...")

        # 1. Killfeed
        payload = {
            "killer": "Phase3_HTTP",
            "victim": "End2End",
            "weapon": "LAR",
            "distance": 800,
            "timestamp": datetime.utcnow().isoformat(),
            "location": "Tisy MB",
        }
        async with session.post(f"{BASE_URL}/test/killfeed", json=payload) as resp:
            log.info(f"Published killfeed: {resp.status} {await resp.text()}")

        await asyncio.sleep(1)

        # 2. Admin Action
        payload = {"type": "KICK", "admin": "AutoMod", "target": "Spammer99", "reason": "Spamming"}
        async with session.post(f"{BASE_URL}/test/admin_action", json=payload) as resp:
            log.info(f"Published admin.action: {resp.status} {await resp.text()}")

        await asyncio.sleep(1)

        # 3. Loot Event
        payload = {"type": "Convoy", "location": "Kabanino", "coords": "5000, 8000", "tier": "Military"}
        async with session.post(f"{BASE_URL}/test/loot_event", json=payload) as resp:
            log.info(f"Published loot.event: {resp.status} {await resp.text()}")

        log.info("🏁 All events emitted.")


if __name__ == "__main__":
    asyncio.run(emit_events())
