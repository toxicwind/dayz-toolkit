import discord
from discord.ext import commands
import logging
from src.mildlyawesome.core.bus import bus

log = logging.getLogger("mildlyawesome.killfeed_cog")

class Killfeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        from src.mildlyawesome.services.killfeed.engine import KillfeedEngine
        self.engine = KillfeedEngine(bot.settings)
        
    async def cog_load(self):
        # Let the engine handle the parsing
        await self.engine.initialize()
        
        # We only listen for the broadcast results
        bus.subscribe("killfeed.broadcast", self.on_killfeed_broadcast)
        log.info("⚔️ Killfeed Cog: Ready for Broadcasts")

    async def on_killfeed_broadcast(self, combat_event):
        log.info(f"⚔️ Killfeed Broadcast: {combat_event.victim_name} pk'd by {combat_event.killer_name}")
        channel_id = self.bot.settings.discord.killfeed_channel_id
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                embed = discord.Embed(
                    title="⚔️ Combat Report",
                    description=f"**{combat_event.killer_name}** killed **{combat_event.victim_name}**",
                    color=discord.Color.red()
                )
                embed.add_field(name="Weapon", value=combat_event.weapon or "Unknown", inline=True)
                embed.add_field(name="Distance", value=f"{combat_event.distance}m" if combat_event.distance else "N/A", inline=True)
                await channel.send(embed=embed)
            else:
                log.warning(f"Killfeed channel {channel_id} not found.")

async def setup(bot):
    await bot.add_cog(Killfeed(bot))
