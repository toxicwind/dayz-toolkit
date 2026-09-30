from __future__ import annotations

import asyncio
import logging
from typing import Optional

import discord
from discord import app_commands
from dotenv import load_dotenv

from .config import load_settings, Settings
from .a2s_query import (
    query_info,
    query_players,
    A2SUnavailableError,
    A2SQueryError,
    A2SOptions,
    configure as configure_a2s,
)
from .bercon import run_rcon
from .stat_channels import parse_stat_channels, update_stat_channels
from .metrics import (
    start_metrics,
    A2S_UP,
    A2S_STALE,
    A2S_ERRORS,
    A2S_PLAYERS,
    A2S_MAX_PLAYERS,
    RCON_UP,
    RCON_ERRORS,
)
from .database import Database
from .voice import VoiceManager, register_voice_commands

log = logging.getLogger("dayz-discord-ops")

def _has_admin_role(member: discord.Member, admin_role_ids: tuple[int, ...]) -> bool:
    role_ids = {r.id for r in member.roles}
    return any(rid in role_ids for rid in admin_role_ids)

class OpsBot(discord.Client):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = settings.use_presence
        intents.presences = settings.use_presence

        super().__init__(intents=intents)
        self.settings = settings
        self.tree = app_commands.CommandTree(self)
        self.stat_cfg = parse_stat_channels(settings.stat_channels_json)
        self._stat_task: Optional[asyncio.Task[None]] = None
        
        # Initialize Database
        self.db = Database(settings)
        self.db.connect()
        
        # Initialize Voice Manager
        self.voice_manager = VoiceManager(self)

    async def setup_hook(self) -> None:
        guild = discord.Object(id=self.settings.discord_guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_ready(self) -> None:
        log.info("Logged in as %s", self.user)
        if self._stat_task is None:
            # Run one immediate tick on startup/ready to verify perms immediately
            await self.stat_tick()
            self._stat_task = asyncio.create_task(self._stat_loop())

    async def _stat_loop(self) -> None:
        while True:
            try:
                await self.stat_tick()
            except Exception:
                log.exception("stat tick failed")
            await asyncio.sleep(600)

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
        try:
            info = query_info(self.settings.dayz_host, self.settings.dayz_query_port)
            A2S_UP.set(0 if info.stale else 1)
            A2S_STALE.set(1 if info.stale else 0)
            if info.last_error_reason:
                A2S_ERRORS.labels(reason=info.last_error_reason).inc()
            A2S_PLAYERS.set(info.players)
            A2S_MAX_PLAYERS.set(info.max_players)
            dayz_players_count = info.players

            # Log to database
            self.db.log_stats(info.players, info.max_players)

        except A2SUnavailableError as exc:
            A2S_UP.set(0)
            A2S_STALE.set(0)
            A2S_ERRORS.labels(reason="unavailable").inc()
            log.warning("A2S module unavailable: %s", exc)
        except A2SQueryError as exc:
            A2S_UP.set(0)
            A2S_STALE.set(0)
            A2S_ERRORS.labels(reason=exc.reason).inc()
            log.warning("A2S query failed: %s", exc)
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
        )

def _format_block(s: str, limit: int = 1800) -> str:
    s = s.strip()
    if len(s) > limit:
        s = s[:limit] + "…"
    return f"```{s}```"

def make_commands(bot: OpsBot) -> None:
    @bot.tree.command(name="dayz_status", description="Show DayZ A2S server info")
    async def dayz_status(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            info = query_info(bot.settings.dayz_host, bot.settings.dayz_query_port)
            A2S_UP.set(0 if info.stale else 1)
            A2S_STALE.set(1 if info.stale else 0)
            if info.last_error_reason:
                A2S_ERRORS.labels(reason=info.last_error_reason).inc()
            A2S_PLAYERS.set(info.players)
            A2S_MAX_PLAYERS.set(info.max_players)
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
            await interaction.followup.send(_format_block(msg), ephemeral=True)
        except A2SUnavailableError as exc:
            A2S_UP.set(0)
            A2S_STALE.set(0)
            A2S_ERRORS.labels(reason="unavailable").inc()
            await interaction.followup.send(
                _format_block(f"A2S unavailable: {exc}"), ephemeral=True
            )
        except A2SQueryError as exc:
            A2S_UP.set(0)
            A2S_STALE.set(0)
            A2S_ERRORS.labels(reason=exc.reason).inc()
            await interaction.followup.send(
                _format_block(f"A2S query failed: {exc}"), ephemeral=True
            )
        except Exception as exc:
            A2S_UP.set(0)
            log.exception("Unhandled dayz_status failure")
            await interaction.followup.send(
                _format_block(f"A2S failed: {type(exc).__name__}: {exc}"), ephemeral=True
            )

    @bot.tree.command(name="dayz_players", description="List DayZ players (A2S)")
    async def dayz_players_cmd(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            players = query_players(bot.settings.dayz_host, bot.settings.dayz_query_port)
            if players.last_error_reason:
                A2S_ERRORS.labels(reason=players.last_error_reason).inc()
            payload = "\n".join(players.names) if players.names else "No players (or names hidden)."
            if players.stale:
                payload += "\n(Data is stale; last live query failed.)"
            await interaction.followup.send(
                _format_block(payload),
                ephemeral=True,
            )
        except A2SUnavailableError as exc:
            A2S_ERRORS.labels(reason="unavailable").inc()
            await interaction.followup.send(
                _format_block(f"A2S unavailable: {exc}"), ephemeral=True
            )
        except A2SQueryError as exc:
            A2S_ERRORS.labels(reason=exc.reason).inc()
            await interaction.followup.send(
                _format_block(f"A2S players failed: {exc}"), ephemeral=True
            )
        except Exception as exc:
            log.exception("Unhandled dayz_players failure")
            await interaction.followup.send(
                _format_block(f"A2S players failed: {type(exc).__name__}: {exc}"),
                ephemeral=True,
            )

    @bot.tree.command(name="dayz_rcon_raw", description="Run a BattlEye RCON command (admin roles only)")
    @app_commands.describe(command="BattlEye RCON command, e.g. 'players' or 'say -1 hello'")
    async def dayz_rcon_raw(interaction: discord.Interaction, command: str) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("Not in a guild context.", ephemeral=True)
            return
        if not _has_admin_role(member, bot.settings.discord_admin_role_ids):
            await interaction.response.send_message("Not allowed.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True, ephemeral=True)
        res = run_rcon(bot.settings.dayz_host, bot.settings.dayz_rcon_port, bot.settings.dayz_rcon_password, command)
        if res.ok:
            RCON_UP.set(1)
            await interaction.followup.send(_format_block(res.response), ephemeral=True)
        else:
            RCON_UP.set(0)
            RCON_ERRORS.inc()
            await interaction.followup.send(_format_block(res.response), ephemeral=True)

    @bot.tree.command(name="stat_tick", description="Force a stat-channel update tick now")
    async def stat_tick_cmd(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        await bot.stat_tick()
        await interaction.followup.send("OK", ephemeral=True)

def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    s = load_settings()
    configure_a2s(
        A2SOptions(
            timeout_s=s.a2s_timeout,
            retries=s.a2s_retries,
            retry_backoff=s.a2s_retry_backoff,
            cache_ttl=s.a2s_cache_ttl,
        )
    )
    if s.metrics_enable:
        start_metrics(s.metrics_port)
        log.info("Metrics enabled on :%d", s.metrics_port)
    bot = OpsBot(s)
    make_commands(bot)
    
    # Register voice commands
    admin_checker = lambda member: _has_admin_role(member, s.discord_admin_role_ids)
    register_voice_commands(bot, bot.voice_manager, admin_checker)
    
    bot.run(s.discord_token)

if __name__ == "__main__":
    main()
