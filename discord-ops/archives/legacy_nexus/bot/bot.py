from __future__ import annotations

import asyncio
import logging
import os
import re
import io
from datetime import datetime
from typing import Optional, Dict, List

import discord
from discord import app_commands
from discord.ext import commands

from .config import load_settings, Settings
from .a2s_query import (
    query_info,
    query_players,
    A2SUnavailableError,
    A2SQueryError,
    A2SOptions,
    configure as configure_a2s,
)
from .stat_channels import parse_stat_channels, update_stat_channels
from .metrics import (
    start_metrics,
    A2S_UP,
    A2S_STALE,
    A2S_ERRORS,
    A2S_PLAYERS,
    A2S_MAX_PLAYERS,
)
from .database import Database
from .voice import VoiceManager, register_voice_commands
from .killfeed import KillfeedManager
from .changelog_manager import ChangelogManager
from .image_generator import get_image_generator
from .services.ftp_service import FTPService

log = logging.getLogger("dayz-discord-ops")

def _has_admin_role(member: discord.Member, admin_role_ids: List[int]) -> bool:
    if not admin_role_ids:
        return False
    role_ids = {r.id for r in getattr(member, "roles", [])}
    return any(rid in role_ids for rid in admin_role_ids)

def _overall_a2s_deadline(settings: Settings) -> float:
    # Each port try can take T + T*B + T*B^2 ...
    # Simplified: T * (retries + 1) * (2.0 max backoff avg) * num_ports
    num_ports = len(settings.a2s_port_offsets)
    per_port = settings.a2s_timeout * (settings.a2s_retries + 1) * 2.0 
    return (per_port * num_ports) + 2.0




class OpsBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True # settings.use_presence often needs members intent
        intents.message_content = True
        if settings.use_presence:
            intents.presences = True

        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings
        self.stat_cfg = parse_stat_channels(settings.stat_channels_json)
        self._stat_task: Optional[asyncio.Task[None]] = None
        
        # Initialize Database
        self.db = Database(settings)
        self.last_players: set[str] = set()
        self.changelog = ChangelogManager(base_dir=getattr(settings, "mission_path", "server"))
        self.ftp_service = FTPService(settings)
        
        self.last_a2s: Dict[str, any] = {}
        
        # Initialize Voice Manager
        self.voice_manager = VoiceManager(self)
        self.killfeed_manager: Optional[KillfeedManager] = None
        
        # New Features
        self.server_was_online = True # Assume online to avoid spam on boot
        self.restart_announced = False
        self.pending_changes: Dict[str, List[str]] = {} # org_id -> list of changed files
        self.start_time = datetime.now()

    @property
    def uptime_str(self) -> str:
        delta = datetime.now() - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        return f"{hours}h {minutes}m {seconds}s"


    async def setup_hook(self) -> None:
        guild = discord.Object(id=self.settings.discord_guild_id)
        self.tree.copy_global_to(guild=guild)
        
        # Load Extension Cogs
        extensions = [
            "bot.trader",
            "bot.casino",
            "bot.tickets",
            "bot.cogs.status_board",
            "bot.cogs.changefeed",
            "bot.cogs.selfplay_driver",
            "bot.cogs.channel_audit",
            "bot.cogs.log_intelligence",
            "bot.cogs.engagement",
            "bot.cogs.tracker",
            "bot.cogs.survival_analytics",
            "bot.cogs.todo",
        ]
        
        for ext in extensions:
            try:
                await self.load_extension(ext)
                log.info(f"Loaded extension: {ext}")
            except Exception as e:
                log.error(f"Failed to load extension {ext}: {e}")
        
        # Initialize hot reload in development mode
        if os.getenv("HOT_RELOAD", "false").lower() == "true":
            from .hot_reload import HotReloadManager
            self.hot_reload = HotReloadManager(self, watch_dir="bot")
            self.hot_reload.start()
            log.info("🔥 Hot reload enabled for development")

        if os.getenv("ENABLE_SELFPLAY", "false").lower() == "true":
            try:
                await self.load_extension('bot.cogs.fakeuser_driver')
                log.info("Loaded bot.cogs.fakeuser_driver")
            except Exception as e:
                log.error(f"Failed to load bot.cogs.fakeuser_driver: {e}")

        await self.tree.sync(guild=guild)

    def reload_config(self):
        """Reload configuration and refresh services."""
        self.settings.reload()
        # Refresh services that depend on settings
        self.ftp_service.settings = self.settings
        self.ftp_service.client.host = self.settings.ftp_host
        self.ftp_service.client.port = self.settings.ftp_port
        self.ftp_service.client.user = self.settings.ftp_user
        self.ftp_service.client.passwd = self.settings.ftp_password
        log.info("🔥 Services refreshed after config reload")

    async def on_message(self, message: discord.Message) -> None:
        if message.content.startswith("§SYNTH"):
            # Synthetic Command Dispatcher
            # Format: §SYNTH <user_id> !command
            parts = message.content.split(" ", 2)
            if len(parts) >= 3:
                # Clone message and inject synthetic properties
                message.content = parts[2]
                
                log.info(f"SYNTH: Context check for '{message.content}'...")
                ctx = await self.get_context(message)
                if not ctx.command:
                    # Robust fallback for synthetic commands
                    prefix = "!"
                    if message.content.startswith(prefix):
                        from discord.ext.commands.view import StringView
                        ctx.view = StringView(message.content)
                        ctx.prefix = prefix
                        ctx.view.skip_string(prefix)
                        ctx.invoked_with = ctx.view.get_word()
                        ctx.command = self.get_command(ctx.invoked_with)
                        if ctx.command:
                            log.info(f"SYNTH: Fallback found command: {ctx.command}")

                if ctx.command:
                    log.info(f"SYNTH: Invoking command: {ctx.command} for user {parts[1]}")
                    await self.invoke(ctx)
                else:
                    log.warning(f"SYNTH: Command '{parts[2]}' not contextually valid. Prefix='{self.command_prefix}'")
                    log.info(f"SYNTH: Registered commands: {list(self.all_commands.keys())}")
            return

        # Ignore other bots, but allow §SYNTH messages from self/bots above
        if message.author.bot:
            return
            
        await self.process_commands(message)

    async def on_ready(self) -> None:
        log.info("Logged in as %s", self.user)
        
        # Connect DB
        try:
            if self.db.connect():
                self.db.log_activity(self.settings.org_id, "SYSTEM", f"Bot started: {self.user} connected to {self.settings.dayz_host}", "info")
        except Exception as e:
            log.warning("DB init/connect failed: %s", e)

        if self._stat_task is None:
            await self.stat_tick()
            self._stat_task = asyncio.create_task(self._stat_loop())
        
        if self.settings.killfeed_enabled and self.settings.discord.killfeed_channel_id:
            if self.killfeed_manager is None:
                self.killfeed_manager = KillfeedManager(
                    self, 
                    self.settings.discord.killfeed_channel_id, 
                    death_channel_id=self.settings.discord.deathfeed_channel_id,
                    db=self.db
                )
            try:
                await self.killfeed_manager.start()
            except Exception:
                log.exception("Failed to start killfeed manager")
                
        # Register database log listener
        from .log_streamer import get_streamer
        from .adm_log_parser import ADMLogParser
        streamer = get_streamer()
        
        async def db_log_listener(event):
            if self.db:
                # Log raw activity first
                self.db.log_activity(
                    org_id=self.settings.org_id,
                    activity_type=event.level.upper(), 
                    message=event.message, 
                    severity=event.level if event.level in ('info', 'warning', 'error') else 'info'
                )
                
                # Check for disconnects with coords
                # We wrap in try/except to ensure parsing doesn't break the bot
                try:
                    events = ADMLogParser.parse_log_content(event.message)
                    for e in events:
                        if e['event_type'] == 'disconnect' and 'pos_x' in e:
                            self.db.update_player_pos(
                                e['gamertag'], 
                                e['pos_x'], 
                                e['pos_y'], 
                                e['pos_z']
                            )
                except Exception as ex:
                    log.warning(f"Failed to parse log line for coords: {ex}")
        
        streamer.add_listener(db_log_listener)
        
        # Start log streamer to pull Nitrado logs
        try:
            await streamer.start()
            log.info("Log streamer started successfully")
        except Exception as e:
            log.error(f"Failed to start log streamer: {e}")

    async def _stat_loop(self) -> None:
        interval = float(os.getenv("STAT_INTERVAL_S", "60"))
        while True:
            try:
                await self.stat_tick()
            except Exception:
                log.exception("stat tick failed")
            
            # Changelog/File Scan
            try:
                # In a multi-tenant setup, we'd loop through guilds
                # For now, let's use the default org_id if detectable
                org_id = getattr(self.settings, 'org_id', 'cluster') 
                changes = await self.changelog.scan(org_id)
                if changes:
                    if org_id not in self.pending_changes:
                        self.pending_changes[org_id] = []
                    self.pending_changes[org_id].extend(changes)
                    log.info(f"Detected changes for {org_id}: {changes}")
            except Exception:
                log.exception("Changelog scan failed")
                
            await asyncio.sleep(interval)

    async def _a2s_info_safe(self):
        deadline = float(os.getenv("A2S_OVERALL_TIMEOUT_S", str(_overall_a2s_deadline(self.settings))))
        return await asyncio.wait_for(
            asyncio.to_thread(query_info, self.settings.dayz_host, self.settings.dayz_query_port),
            timeout=deadline,
        )

    async def _a2s_players_safe(self):
        deadline = float(os.getenv("A2S_OVERALL_TIMEOUT_S", str(_overall_a2s_deadline(self.settings))))
        return await asyncio.wait_for(
            asyncio.to_thread(query_players, self.settings.dayz_host, self.settings.dayz_query_port),
            timeout=deadline,
        )

    async def stat_tick(self) -> None:
        guild = self.get_guild(self.settings.discord_guild_id)
        if not guild:
            return

        total = guild.member_count or 0
        online: Optional[int] = None
        if self.settings.use_presence:
            online = sum(
                1 for m in guild.members
                if m.status in (discord.Status.online, discord.Status.idle, discord.Status.dnd)
            )

        dayz_players_count: Optional[int] = None
        dayz_max_players: Optional[int] = None
        
        try:
            info = await self._a2s_info_safe()
            A2S_UP.set(0 if info.stale else 1)
            A2S_STALE.set(1 if info.stale else 0)
            if info.last_error_reason:
                A2S_ERRORS.labels(reason=info.last_error_reason).inc()
            A2S_PLAYERS.set(info.players)
            A2S_MAX_PLAYERS.set(info.max_players)
            dayz_players_count = info.players
            dayz_max_players = info.max_players

            # Protocol SIGMA: Universal Truth Binding
            self.last_a2s = {
                "players": info.players,
                "max_players": info.max_players,
                "version": getattr(info, "version", "1.28-SIGMA"),
                "stale": info.stale,
                "timestamp": datetime.now().isoformat()
            }

            # Activity Tracking (Joins/Leaves)
            try:
                players_res = await self._a2s_players_safe()
                current_players = set(players_res.names)
                
                joining = current_players - self.last_players
                leaving = self.last_players - current_players
                
                for p in joining:
                    await self.db.log_activity(self.settings.org_id, "JOIN", f"Player {p} joined the server", "info")
                for p in leaving:
                    await self.db.log_activity(self.settings.org_id, "LEAVE", f"Player {p} left the server", "info")
                    
                self.last_players = current_players
            except Exception as e:
                log.warning("Player tracking failed: %s", e)

            # Log to database
            try:
                await self.db.log_stats(self.settings.org_id, info.players, info.max_players)
            except Exception as e:
                log.warning("DB log_stats failed: %s", e)

        except (A2SUnavailableError, A2SQueryError, asyncio.TimeoutError) as exc:
            reason = "timeout" if isinstance(exc, asyncio.TimeoutError) else getattr(exc, "reason", "a2s_error")
            A2S_UP.set(0)
            A2S_STALE.set(0)
            A2S_ERRORS.labels(reason=str(reason)).inc()
            log.warning("A2S failed (%s): %s", reason, exc)
            self.db.log_activity(self.settings.org_id, "A2S_FAIL", f"A2S Query failed: {reason}", "warning")
        except Exception:
            A2S_UP.set(0)
            A2S_STALE.set(0)
            log.exception("Unexpected error pulling A2S data")

        await update_stat_channels(
            guild,
            self.stat_cfg,
            members_total=total,
            members_online=online,
            dayz_players=dayz_players_count,
            dayz_max_players=dayz_max_players,
        )
            
        # Restart / Offline Detection
        if self.settings.restart_channel_id:
            channel = self.get_channel(self.settings.restart_channel_id)
            if channel:
                if not isinstance(channel, discord.TextChannel):
                    log.warning(f"Restart channel {self.settings.restart_channel_id} is not a text channel.")
                    return
                is_online = (dayz_players_count is not None)
                
                if self.server_was_online and not is_online:
                    # Server went DOWN
                    await channel.send("🔴 **Server Alert**: Server is currently OFFLINE (or unreachable). Possible restart or crash.")
                    self.server_was_online = False
                
                elif not self.server_was_online and is_online:
                    # Server came UP
                    self.server_was_online = True
                    
                    # Aesthetic Announcement
                    org_id = getattr(self.settings, 'org_id', 'cluster')
                    img_gen = get_image_generator()
                    # Scan for changes
                    changes = await self.changelog.scan(org_id)
                    
                    # Pop pending changes from the _stat_loop if any
                    pending_changes_from_loop = self.pending_changes.pop(org_id, [])
                    if pending_changes_from_loop:
                        changes.extend(pending_changes_from_loop)

                    subtitle = None
                    if changes:
                        # Deduplicate and format
                        unique_changes = sorted(list(set(changes)))
                        summary = ", ".join(unique_changes[:3])
                        if len(unique_changes) > 3:
                            summary += f" and {len(unique_changes)-3} more"
                        subtitle = f"Changes Applied: {summary}"
                    
                    # Read latest changelog entry specifically if available
                    latest_log = await self.changelog.get_latest_changelog_entry(org_id)
                    
                    card_bytes = img_gen.generate_status_card(
                        title=self.settings.name if hasattr(self.settings, 'name') else "DayZ",
                        status_text="Server Online!",
                        subtitle=subtitle
                    )
                    
                    file = discord.File(io.BytesIO(card_bytes), filename="status.png")
                    await channel.send(content="🟢 **Server NOW ONLINE and Updates Applied!**", file=file)
                    
                    # Also post changelog if in a separate channel
                    if latest_log and hasattr(self.settings, 'changelog_channel_id') and self.settings.changelog_channel_id:
                        log_channel = self.get_channel(self.settings.changelog_channel_id)
                        if log_channel:
                            embed = discord.Embed(
                                title="Latest Changelog Entry",
                                description=latest_log,
                                color=discord.Color.gold(),
                                timestamp=datetime.now()
                            )
                            await log_channel.send(embed=embed)


def _format_block(s: str, limit: int = 1800) -> str:
    s = s.strip()
    if len(s) > limit:
        s = s[:limit] + "…"
    return f"```{s}```"

def make_commands(bot: OpsBot) -> None:
    @bot.hybrid_command(name="dayz_status", description="Show DayZ A2S server info")
    async def dayz_status(ctx: commands.Context) -> None:
        try:
            info = await bot._a2s_info_safe()
            msg = (
                f"Server: {info.name}\n"
                f"Map: {info.map}\n"
                f"Players: {info.players}/{info.max_players}\n"
                f"Game: {info.game}\n"
                f"Version: {info.version}\n"
                f"Query: {bot.settings.dayz_host}:{bot.settings.dayz_query_port}\n"
            )
            if info.stale:
                msg += "\n(Data is stale; last live query failed.)"
            
            await ctx.send(_format_block(msg))
        except Exception as e:
            await ctx.send(f"A2S failed: {type(e).__name__}: {e}")


    @bot.hybrid_command(name="dayz_players", description="List DayZ players (A2S)")
    async def dayz_players(ctx: commands.Context) -> None:
        try:
            players = await bot._a2s_players_safe()
            payload = "\n".join(players.names) if players.names else "No players (or names hidden)."
            if players.stale:
                payload += "\n(Data is stale; last live query failed.)"
            await ctx.send(_format_block(payload))
        except Exception as e:
            await ctx.send(_format_block(f"A2S players failed: {type(e).__name__}: {e}"))




    @bot.hybrid_command(name="stat_tick", description="Force a stat-channel update tick now")
    async def stat_tick(ctx: commands.Context) -> None:
        await bot.stat_tick()
        await ctx.send("OK ✅")

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    s = load_settings()
    configure_a2s(
        A2SOptions(
            timeout_s=s.a2s_timeout,
            retries=s.a2s_retries,
            retry_backoff=s.a2s_retry_backoff,
            cache_ttl=int(s.a2s_cache_ttl),
            port_offsets=tuple(s.a2s_port_offsets),
            packet_pad_to=s.a2s_packet_pad_to,
            raw_enable=s.a2s_raw_enable,
            prefer_ipv4=s.a2s_prefer_ipv4,
        )
    )
    if s.metrics_enabled:
        start_metrics(s.metrics_port)
        log.info("Metrics enabled on :%d", s.metrics_port)

    # Create bot instance BEFORE starting API
    bot = OpsBot(s)
    make_commands(bot)
    
    # Register voice commands
    def admin_checker(member):
        return _has_admin_role(member, s.discord_admin_role_ids)
    register_voice_commands(bot, bot.voice_manager, admin_checker)

    # Start API Server in background thread with bot reference
    from . import api
    api._bot_ref = bot
    
    from .api import start_api
    import threading
    api_thread = threading.Thread(
        target=start_api, 
        kwargs={"host": "0.0.0.0", "port": int(os.getenv("DASHBOARD_PORT", 18789))},
        daemon=True
    )
    api_thread.start()
    
    bot.run(s.discord_token)

if __name__ == "__main__":
    main()
