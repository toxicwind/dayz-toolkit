import logging
import asyncio
from discord.ext import commands, tasks
from src.mildlyawesome.nitrado_api import NitradoAPIClient
from src.modules.killfeed.parser import ADMParser
from src.mildlyawesome.services.log_streamer import get_streamer
from datetime import datetime, timedelta

log = logging.getLogger("mildlyawesome.poller")

class LogPoller(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.nitrado = None
        self.parser = ADMParser()
        self.streamer = None
        self.last_log_file = None
        self.last_read_bytes = 0
        self.error_backoff = 0

    async def cog_load(self):
        self.streamer = get_streamer(self.bot.settings)
        token = self.bot.settings.nitrado_token()
        if token:
            self.nitrado = NitradoAPIClient(token)
            self.poll_logs.start()
            log.info("🚀 LogPoller: Started (Interval: 60s)")
        else:
            log.warning("⚠️ LogPoller: No Nitrado token found - disabled.")

    async def cog_unload(self):
        self.poll_logs.cancel()

    @tasks.loop(seconds=60)
    async def poll_logs(self):
        # 1. Get Service ID
        try:
            service_id = self.bot.settings.nitrado_service_id()
            if not service_id:
                # Try to auto-discover if not hardcoded
                services = await self.nitrado.get_services()
                if services.get("status") == "success" and services.get("data", {}).get("services"):
                    service_id = services["data"]["services"][0]["id"]
                    log.info(f"LogPoller: Auto-discovered Service ID {service_id}")
                else:
                    log.error("LogPoller: No service ID configured or discoverable.")
                    return
        except Exception as e:
            log.error(f"LogPoller: Failed to resolve service ID: {e}")
            return

        # 2. Find latest ADM log
        try:
            log_files = await self.nitrado.get_logs_list(service_id)
            # Find newest DayZServer_X1_x64_*.ADM
            adm_logs = [f for f in log_files if "DayZServer" in f and f.endswith(".ADM")]
            if not adm_logs:
                log.debug("No ADM logs found.")
                return

            # Assuming list is sorted or we sort by name (timestamp in desc)
            adm_logs.sort(reverse=True)
            target_log = adm_logs[0]

            if target_log != self.last_log_file:
                log.info(f"LogPoller: New log file detected: {target_log}")
                self.last_log_file = target_log
                self.last_read_bytes = 0 # Reset for new file
        except Exception as e:
            log.error(f"LogPoller: Failed to list logs: {e}")
            return

        # 3. Download & Parse Diff
        try:
            content = await self.nitrado.download_file(service_id, target_log)
            if not content:
                return

            current_size = len(content)
            if current_size <= self.last_read_bytes:
                return # No new data

            new_data = content[self.last_read_bytes:]
            self.last_read_bytes = current_size

            # Parse new lines
            # Note: Content might be partial line at end? Usually API gives full file.
            # We assume 'new_data' aligns with new lines mostly.
            # Ideally we split by lines.

            lines = new_data.splitlines()
            events = []
            for line in lines:
                if not line.strip(): continue
                evt = self.parser.parse_line(line) # Returns dict
                if evt:
                    # Convert to LogEvent object if Streamer expects one?
                    # get_streamer uses 'LogEvent' from src.mildlyawesome.services.parsers.base
                    # But ADMParser returns a dict.
                    # We should check what LogStreamer expects.
                    # Looking at selfplay_driver, it creates LogEvent objects.
                    # Let's import LogEvent here.
                    from src.mildlyawesome.services.parsers.base import LogEvent

                    # Map dict to LogEvent
                    # evt dict keys: timestamp, type, player_name, player_id, etc.
                    log_event = LogEvent(
                        timestamp=evt.get("timestamp"),
                        source="nitrado_adm",
                        level=evt.get("type", "info"),
                        message=line,
                        raw=line,
                        data=evt
                    )
                    events.append(log_event)

            if events:
                log.info(f"LogPoller: Ingested {len(events)} new events")
                for e in events:
                    await self.streamer._notify_listeners(e)

        except Exception as e:
            log.error(f"LogPoller: Download/Parse cycle failed: {e}")

    @poll_logs.before_loop
    async def before_poll(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(LogPoller(bot))
