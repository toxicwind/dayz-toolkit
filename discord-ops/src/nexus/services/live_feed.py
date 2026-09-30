import asyncio
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord.ext import tasks

from ..log_streamer import LogEvent, get_streamer

log = logging.getLogger("mildlyawesome.services.live_feed")

class LiveFeedService:
    def __init__(self, bot):
        self.bot = bot
        self.buffer = deque(maxlen=200)
        self.last_flush = datetime.utcnow()
        self.flush_lock = asyncio.Lock()
        
        # Poller Stats
        self.events_processed = 0
        self.start_time = datetime.utcnow()
        self._poller_msg: Optional[discord.Message] = None

    async def start(self):
        """Start the live feed service."""
        streamer = get_streamer()
        streamer.add_listener(self._on_log_event)
        self.flush_task.start()
        self.poller_task.start()
        log.info("LiveFeedService started")

    async def stop(self):
        streamer = get_streamer()
        streamer.remove_listener(self._on_log_event)
        self.flush_task.cancel()
        self.poller_task.cancel()

    async def _on_log_event(self, event: LogEvent):
        """Buffer/Handle incoming log event."""
        self.events_processed += 1
        
        # Format for readability
        # E.g. [12:00:01] [NITRADO] [INFO] Player 'Survivor' connected
        ts = datetime.fromisoformat(event.timestamp).strftime("%H:%M:%S")
        line = f"`[{ts}]` **[{event.source.upper()}]** `[{event.level.upper()}]` {discord.utils.escape_markdown(event.message)}"
        
        self.buffer.append(line)

    @tasks.loop(seconds=2.0)
    async def flush_task(self):
        """Flush buffered logs to Discord channel."""
        if not self.buffer:
            return

        channel_id = self.bot.registry.resolve("ops.livefeed")
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        async with self.flush_lock:
            # Drain buffer
            lines = []
            while self.buffer and len(lines) < 15: # Batch size
                lines.append(self.buffer.popleft())
            
            if not lines:
                return

            chunk = "\n".join(lines)
            try:
                await channel.send(chunk)
            except Exception as e:
                log.warning(f"Failed to send live feed batch: {e}")

    @tasks.loop(seconds=10.0)
    async def poller_task(self):
        """Update the Live Poller Status Dashboard."""
        channel_id = self.bot.registry.resolve("ops.livepoller")
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        # Prepare Embed
        uptime = datetime.utcnow() - self.start_time
        streamer = get_streamer()
        
        embed = discord.Embed(
            title="🔄 Chronos Live Poller",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Uptime", value=str(uptime).split('.')[0], inline=True)
        embed.add_field(name="Events Processed", value=str(self.events_processed), inline=True)
        embed.add_field(name="Buffer Size", value=str(len(self.buffer)), inline=True)
        
        embed.add_field(name="WS Clients", value=str(len(streamer.clients)), inline=True)
        embed.add_field(name="Platform", value=streamer.platform, inline=True)
        
        embed.set_footer(text="Updates every 10s • Chronos-Forge")

        try:
            # Edit existing or send new
            if self._poller_msg:
                try:
                    await self._poller_msg.edit(embed=embed)
                    return
                except discord.NotFound:
                    self._poller_msg = None # Message deleted, send new one
            
            # Find last message by bot to update? Or just send new?
            # Ideally we check history if we lost ref
            if not self._poller_msg:
                # Simple Purge-and-Post strategy for a status channel
                # (Optional: purge old messages to keep channel clean)
                # await channel.purge(limit=5, check=lambda m: m.author == self.bot.user)
                self._poller_msg = await channel.send(embed=embed)
                
        except Exception as e:
            log.warning(f"Failed to update poller: {e}")

    @flush_task.before_loop
    @poller_task.before_loop
    async def before_loops(self):
        await self.bot.wait_until_ready()
