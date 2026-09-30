import discord
from discord.ext import commands
import logging
from src.mildlyawesome.core.config import MildlyAwesomeSettings
from src.mildlyawesome.core.bus import bus
from src.mildlyawesome.services.log_streamer import get_streamer

log = logging.getLogger("mildlyawesome.bot")

class OpsBot(commands.Bot):
    def __init__(self, settings: MildlyAwesomeSettings):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings
        self.streamer = get_streamer(settings)
        
    async def setup_hook(self):
        log.info("🔥 MildlyAwesome Ignition: Loading Hardened Cogs")
        
        # Load extensions
        extensions = [
            "src.mildlyawesome.bot.cogs.killfeed",
            "src.mildlyawesome.bot.cogs.status_board",
            "src.mildlyawesome.bot.cogs.selfplay_driver",
        ]
        
        for ext in extensions:
            try:
                await self.load_extension(ext)
                log.info(f"✅ Loaded {ext}")
            except Exception as e:
                log.error(f"❌ Failed to load {ext}: {e}")

    async def on_ready(self):
        log.info(f"🤖 Bot Online: {self.user} (Identity: {self.settings.org_id})")
        # Ensure StatusBoard task is running or other init logic
