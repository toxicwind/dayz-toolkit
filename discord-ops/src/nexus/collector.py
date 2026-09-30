
import asyncio
import logging
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)

class DediAgentCollector:
    def __init__(self, agent_url="http://agent_app:35100"):
        self.agent_url = agent_url
        self.metrics = {}

    async def fetch_autopsy(self):
        """Fetches self-diagnostic data from Dedi-Agent."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.agent_url}/meta/autopsy", timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.metrics = data
                        logger.info(f"Collected autopsy data: {data.get('identity')}")
                        return data
                    else:
                        logger.error(f"Failed to fetch autopsy: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching autopsy: {e}")
            return None

    async def start_collection_loop(self, interval=60):
        while True:
            await self.fetch_autopsy()
            await asyncio.sleep(interval)
