import discord
from discord.ext import commands
import logging
import asyncio
from src.mildlyawesome.services.log_streamer import get_streamer
from src.mildlyawesome.services.parsers.base import LogEvent
from datetime import datetime

log = logging.getLogger("mildlyawesome.selfplay")

class SelfPlayDriver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.streamer = get_streamer(bot.settings)
        from src.mildlyawesome.core.bus import bus
        self.bus = bus

    async def cog_load(self):
        self.bus.subscribe("demo.mode.start", self.on_demo_start)
        log.info("🚀 SelfPlayDriver: Subscribed to demo.mode.start")

    async def on_demo_start(self, data):
        log.info(f"🚀 SelfPlayDriver: Received demo start event: {data}")
        await self.run_simulation()

    @commands.command(name="startDemoMode")
    @commands.is_owner()
    async def start_demo(self, ctx):
        await ctx.send("🚀 Starting Full Live Demo Mode...")
        await self.run_simulation()

    async def run_simulation(self):
        log.info("SELFPLAY: Starting simulation sequence...")
        
        # Simulate combat event
        mock_line = '2025-12-26 05:00:00 | Player "Victim" (DEAD) (id=ABC pos=<4650.5, 150.0, 8300.2>) killed by Player "ToxicWind" (id=DEF pos=<4800.0, 160.0, 8400.0>) with M4A1 from 185.5 meters'
        
        event = LogEvent(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            source="rcon",
            level="combat",
            message=mock_line,
            raw=mock_line
        )
        
        await self.streamer._notify_listeners(event)
        log.info("SELFPLAY: Emitted mock combat event.")

async def setup(bot):
    await bot.add_cog(SelfPlayDriver(bot))
