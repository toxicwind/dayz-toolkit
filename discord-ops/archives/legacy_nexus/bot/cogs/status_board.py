import discord
from discord.ext import tasks, commands
from discord import ui
import asyncio
import time
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import aiohttp

log = logging.getLogger(__name__)

class StatusView(ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @ui.button(label="Refresh", style=discord.ButtonStyle.gray, custom_id="status:refresh")
    async def refresh(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self.cog.update_status()
        await interaction.followup.send("Status refreshed!", ephemeral=True)

    @ui.button(label="Probe Details", style=discord.ButtonStyle.blurple, custom_id="status:probes")
    async def probes(self, interaction: discord.Interaction, button: ui.Button):
        status = self.cog.last_status or {}
        embed = discord.Embed(title="🔍 Probe Diagnostics", color=discord.Color.blue())
        for k, v in status.items():
            embed.add_field(name=k.upper(), value=f"```json\n{v}\n```", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class StatusBoard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_status = {}
        self.status_message_id = None
        self.channel_id = None
        self.db_path = Path("state/status_board.db")
        self.last_state_ts = time.time()
        self.last_known_state = "unknown"
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=20.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS server_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                status TEXT,
                players INTEGER,
                duration REAL
            )
        """)
        conn.commit()
        
        # Load state
        cursor = conn.execute("SELECT value FROM state WHERE key = 'message_id'")
        row = cursor.fetchone()
        if row and row[0] and row[0] != "None": 
            try: self.status_message_id = int(row[0])
            except: self.status_message_id = None
        
        cursor = conn.execute("SELECT value FROM state WHERE key = 'channel_id'")
        row = cursor.fetchone()
        if row and row[0] and row[0] != "None": 
            try: self.channel_id = int(row[0])
            except: self.channel_id = None
        conn.close()

    def _save_state(self):
        conn = sqlite3.connect(str(self.db_path), timeout=20.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('message_id', ?)", (str(self.status_message_id),))
        conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('channel_id', ?)", (str(self.channel_id),))
        conn.commit()
        conn.close()

    async def cog_load(self):
        self.update_loop.start()

    async def cog_unload(self):
        self.update_loop.cancel()

    async def ensure_message(self):
        """Finds or creates the single pinned status message"""
        guild_id = self.bot.settings.discord.guild_id
        if not guild_id: return
        
        guild = self.bot.get_guild(guild_id)
        if not guild: return

        # Find or create channel
        channel_name = f"🟢-{self.bot.settings.org_id}-status"
        channel = None
        
        # 1. Use memory ID
        if self.channel_id:
            channel = self.bot.get_channel(self.channel_id)
        
        # 2. Use config ID
        if not channel and getattr(self.bot.settings.discord, 'status_channel_id', None):
            channel = self.bot.get_channel(self.bot.settings.discord.status_channel_id)
            if channel:
                self.channel_id = channel.id
                self._save_state()

        # 3. Fallback to name search
        if not channel:
            channel = discord.utils.get(guild.text_channels, name=channel_name)
        
        # 4. Create if absolutely missing
        if not channel:
            channel = await guild.create_text_channel(channel_name)
            self.channel_id = channel.id
            self._save_state()

        # Find or create message
        message = None
        if self.status_message_id:
            try:
                message = await channel.fetch_message(self.status_message_id)
            except:
                pass
        
        if not message:
            async for msg in channel.history(limit=50):
                if msg.author == self.bot.user and msg.embeds:
                    message = msg
                    break
        
        if not message:
            embed = discord.Embed(title="Initializing Status Board...", color=discord.Color.orange())
            message = await channel.send(embed=embed, view=StatusView(self))
            self.status_message_id = message.id
            self._save_state()
            try: await message.pin()
            except: pass
        
        return message

    async def probe_nitrado(self) -> Dict[str, Any]:
        token = self.bot.settings.nitrado.api_token
        sid = self.bot.settings.nitrado.service_id
        if not token or not sid: return {"status": "error", "message": "Missing credentials"}
        
        url = f"https://api.nitrado.net/services/{sid}/gameservers"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get('data', {}).get('gameserver', {})
                    return {"status": "error", "code": resp.status}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _log_event(self, status: str, players: int, duration: float = 0):
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            conn.execute(
                "INSERT INTO server_events (timestamp, status, players, duration) VALUES (?, ?, ?, ?)",
                (time.time(), status, players, duration)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            log.error(f"Failed to log event: {e}")

    async def _notify_status_change(self, new_status: str, duration: float):
        if new_status == 'started':
            msg = f"🟢 **Server is BACK ONLINE!**\n⏱️ Downtime: `{duration:.0f}s`"
            # Tag admin/here if long downtime? Nah.
        elif new_status == 'stopped' or new_status == 'restarting':
            msg = f"🔴 **Server Status Change: {new_status.upper()}**"
        else:
            return

        # Use changefeed channel first, fallback to status channel location
        cid = self.bot.settings.discord.changefeed_channel_id or self.channel_id
        if cid:
            try:
                channel = self.bot.get_channel(cid)
                if channel:
                   await channel.send(msg)
            except Exception as e:
                log.error(f"Failed to send notification: {e}")

    async def update_status(self):
        msg = await self.ensure_message()
        if not msg: return

        # Probes
        nitrado = await self.probe_nitrado()
        self.last_status['nitrado'] = nitrado
        
        # State Tracking
        current_state = nitrado.get('status', 'unknown')
        players = nitrado.get('query', {}).get('player_current', 0)
        
        now = time.time()
        if current_state != self.last_known_state:
            duration = now - self.last_state_ts
            
            # Log
            self._log_event(current_state, players, duration)
            
            # Notify
            if self.last_known_state != 'unknown':
                await self._notify_status_change(current_state, duration)
            
            self.last_known_state = current_state
            self.last_state_ts = now
        
        online = nitrado.get('status') == 'started'
        players = nitrado.get('query', {}).get('player_current', 0)
        max_players = nitrado.get('query', {}).get('player_max', 60)
        
        color = discord.Color.green() if online else discord.Color.red()
        emoji = "🟢" if online else "🔴"
        
        embed = discord.Embed(
            title=f"{emoji} Server Status: {nitrado.get('query', {}).get('server_name', 'DayZ Server')}",
            color=color,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="State", value=f"**{nitrado.get('status', 'Unknown').upper()}**", inline=True)
        embed.add_field(name="Players", value=f"**{players} / {max_players}**", inline=True)
        embed.add_field(name="Version", value=f"`{nitrado.get('query', {}).get('version', 'N/A')}`", inline=True)
        
        # Build Info
        embed.add_field(name="Build Stamp", value=f"SHA: `{getattr(self.bot.settings, 'git_sha', 'HEAD')[:7]}`", inline=True)
        embed.add_field(name="Profile", value=f"`{self.bot.settings.org_id}`", inline=True)
        
        # Meta
        embed.set_footer(text="Last Updated")
        
        try:
            await msg.edit(embed=embed, view=StatusView(self))
        except Exception as e:
            log.error(f"Failed to edit status message: {e}")

    @tasks.loop(seconds=60, reconnect=True)
    async def update_loop(self):
        try:
            await self.update_status()
        except Exception as e:
            log.error(f"Status loop error: {e}")

    @update_loop.before_loop
    async def before_update_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(StatusBoard(bot))
