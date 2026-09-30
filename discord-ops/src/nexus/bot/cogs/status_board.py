import discord
from discord.ext import commands, tasks
import logging
import random

log = logging.getLogger("mildlyawesome.status")

class StatusBoard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_status.start()

    def cog_unload(self):
        self.update_status.cancel()

    @tasks.loop(minutes=5)
    async def update_status(self):
        """Simulate probing Nitrado for status updates."""
        if not self.bot.is_ready():
            return
            
        log.info("StatusBoard: Probing server status...")
        # Mocking for now
        player_count = random.randint(10, 50)
        await self.bot.change_presence(
            activity=discord.Game(name=f"EZStreet | {player_count}/60 Players")
        )

    async def probe_nitrado(self):
        # Mock probe
        return {"status": "started", "players": random.randint(10, 50)}

async def setup(bot):
    await bot.add_cog(StatusBoard(bot))
