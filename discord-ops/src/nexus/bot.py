from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

import discord
from discord.ext import commands
import aiohttp
from .config import DiscordLiveUpdateSettings
from .discord_live_updates import DiscordLiveConfig, DiscordLiveUpdates
from .discord_registry import DiscordRegistry

# module-scope singletons to prevent reconnect duplication
_discord_live: DiscordLiveUpdates | None = None
_discord_live_started: bool = False

from .a2s_query import (
    A2SOptions,
)
from .a2s_query import (
    configure as configure_a2s,
)
from .changelog_manager import ChangelogManager
from .config import Settings, load_settings
from .database import Database
from .discord_ingest_store import ChannelStatus
from .discord_ingest_store import store as ingest_store
from .killfeed import KillfeedManager
from .metrics import start_metrics
from .services.ftp_service import FTPService
from .voice import VoiceManager, register_voice_commands

log = logging.getLogger("dayz-discord-ops")


def _has_admin_role(member: discord.Member, admin_role_ids: list[int]) -> bool:
    if not admin_role_ids:
        return False
    role_ids = {r.id for r in getattr(member, "roles", [])}
    return any(rid in role_ids for rid in admin_role_ids)


class OpsBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True
        if settings.use_presence:
            intents.presences = True

        super().__init__(command_prefix="!", intents=intents)

        self.settings = settings

        # Initialize Database
        self.db = Database(settings)
        self.changelog = ChangelogManager(base_dir=getattr(settings, "mission_path", "server"))
        self.ftp_service = FTPService(settings)

        # Initialize Registry
        repo_root = Path(__file__).parent.parent.parent
        self.registry = DiscordRegistry(repo_root)

        # Initialize Voice Manager
        self.voice_manager = VoiceManager(self)
        self.killfeed_manager: KillfeedManager | None = None

        # Initialize Core Substrate
        from .supervisor import Supervisor

        self.supervisor = Supervisor()
        self.supervisor.start()

        from .events import get_bus

        self.event_bus = get_bus()

        # Discord ingest store (shared with API thread)
        self.ingest_store = ingest_store

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

async def _start_discord_live_updates_once(bot: "OpsBot") -> None:
    global _discord_live, _discord_live_started
    if _discord_live_started:
        # ensure bot has reference even if started (e.g. hot reload edge case)
        if _discord_live and not hasattr(bot, "discord_live"):
            bot.discord_live = _discord_live
        return
    s = DiscordLiveUpdateSettings()
    if not (s.STATUS_WEBHOOK_URL and s.ADMIN_WEBHOOK_URL):
        print("[discord_live_updates] missing webhook env; module disabled")
        _discord_live_started = True
        return
    session = aiohttp.ClientSession()
    cfg = DiscordLiveConfig(
        status_webhook_url=s.STATUS_WEBHOOK_URL,
        killfeed_webhook_url=s.KILLFEED_WEBHOOK_URL or s.ADMIN_WEBHOOK_URL,
        admin_webhook_url=s.ADMIN_WEBHOOK_URL,
        loot_webhook_url=s.LOOT_WEBHOOK_URL or s.ADMIN_WEBHOOK_URL,
        status_interval_s=s.STATUS_INTERVAL_S,
        burst_window_s=s.BURST_WINDOW_S,
        max_queue=s.MAX_QUEUE,
        state_path=s.STATE_PATH,
    )
    _discord_live = DiscordLiveUpdates(cfg, session=session)
    _discord_live.start()

    # Attach to bot for modules
    bot.discord_live = _discord_live

    # smoke test proves substrate immediately
    await _discord_live.smoke()
    _discord_live_started = True

    async def setup_hook(self) -> None:
        guild = discord.Object(id=self.settings.discord_guild_id)
        self.tree.copy_global_to(guild=guild)

        # 1. Load Legacy Extensions (to be deprecated)
        legacy_extensions = [
            # "src.mildlyawesome.cogs.log_intelligence", # Disabled in favor of modular
            "src.mildlyawesome.cogs.log_poller",
            "src.mildlyawesome.cogs.selfplay_driver",
            "src.mildlyawesome.cogs.channel_audit"
        ]

        for ext in legacy_extensions:
            try:
                await self.load_extension(ext)
                log.info(f"Loaded legacy extension: {ext}")
            except Exception as e:
                log.error(f"Failed to load legacy extension {ext}: {e}")

        # 2. Dynamic Module Discovery (modules/*/bot.py)
        modules_dir = Path(__file__).parent.parent / "modules"
        if modules_dir.exists():
            for module_path in modules_dir.iterdir():
                if module_path.is_dir() and (module_path / "bot.py").exists():
                    ext = f"src.modules.{module_path.name}.bot"
                    try:
                        await self.load_extension(ext)
                        log.info(f"Loaded modular extension: {ext}")
                    except Exception as e:
                        log.error(f"Failed to load modular extension {ext}: {e}")

        # Initialize hot reload in development mode
        if os.getenv("HOT_RELOAD", "false").lower() == "true":
            from .hot_reload import HotReloadManager

            self.hot_reload = HotReloadManager(self, watch_dir=".")
            self.hot_reload.start()
            log.info("🔥 Hot reload enabled for development")
        # Initialize critical subsystems
        try:
            # 1. High-Fidelity Event Bus Worker
            await self.supervisor.spawn("event_bus", self.event_bus.start)

            # 2. Supervisor Monitor
            await self.supervisor.spawn("supervisor_monitor", self.supervisor.monitor)

            # 3. Live Updates (Background setup)
            # 3. Live Updates (Background setup)
            # from .discord_live_updates import setup as setup_live_updates
            # await setup_live_updates(self)
            # 3. Live Updates (Background setup)
            # from .discord_live_updates import setup as setup_live_updates
            # await setup_live_updates(self)
            await _start_discord_live_updates_once(self)

            # 4. Health Monitor
            from .health_monitor import start_monitoring
            await self.supervisor.spawn("health_monitor", start_monitoring)

            log.info("✅ High-Fidelity Core initialized (EventBus worker, Supervisor monitor)")
        except Exception as e:
            log.error(f"Failed to setup core systems: {e}", exc_info=True)

        try:
            await self.tree.sync(guild=guild)
            log.info(f"✅ Slash commands synced to guild {guild.id}")
        except discord.Forbidden:
            log.warning(f"⚠️ Failed to sync commands to guild {guild.id}: Missing Access (Check Bot Invite/Scopes)")
        except Exception as e:
            log.error(f"❌ Failed to sync commands: {e}")

        # Channel validation + backfill on startup
        await self._validate_and_backfill_channels()

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        # Record event for ingest matrix
        try:
            self.ingest_store.record_event(
                message_id=message.id,
                channel_id=message.channel.id,
                channel_tag=getattr(message.channel, "name", str(message.channel.id)),
                author=str(message.author),
                author_id=message.author.id,
                content=message.content or "",
                created_at=message.created_at.replace(tzinfo=None),
            )
        except Exception as e:
            log.warning(f"[CHANNEL_MATRIX] record_event failed: {e}")
        await self.process_commands(message)

    def _tracked_channels(self) -> dict[str, int]:
        # Registry-ONLY resolution (Chronos Mandate)
        reg = self.registry
        return {
            "status": reg.resolve("ops.status") or 0,
            "killfeed": reg.resolve("ops.killfeed") or 0,
            "deathfeed": reg.resolve("ops.deathfeed") or 0,
            "changefeed": reg.resolve("ops.changefeed") or 0,
            "admin": reg.resolve("ops.admin") or 0,
            "server_status": reg.resolve("ops.server_status") or 0,
            "admin_log": reg.resolve("ops.admin_log") or 0,
            "loot_events": reg.resolve("ops.loot_events") or 0,
            "todo": reg.resolve("ops.todo") or 0,
            "livefeed": reg.resolve("ops.livefeed") or 0,
            "livepoller": reg.resolve("ops.livepoller") or 0,
        }

    async def _validate_and_backfill_channels(self):
        """Validate tracked channels and backfill last N messages."""
        tracked = self._tracked_channels()
        if not tracked:
            log.warning("[CHANNEL_MATRIX] No tracked channels configured")
            return

        guild = self.get_guild(self.settings.discord_guild_id)
        if not guild:
            log.error("[CHANNEL_MATRIX] Guild not found")
            return

        tasks = []
        for tag, chan_id in tracked.items():
            if not chan_id:
                continue
            tasks.append(self._validate_channel(guild, tag, chan_id))
        if tasks:
            await asyncio.gather(*tasks)

        # Log Validation Summary
        matrix = self.ingest_store.get_status_matrix()
        passed = []
        failed = []

        for item in matrix:
            tag = item.get("tag", str(item.get("channel_id")))
            if item.get("exists") and item.get("can_read"):
                passed.append(tag)
            else:
                extra = f"(Err: {item.get('last_error')})" if item.get("last_error") else "(Missing/Perms)"
                failed.append(f"{tag}{extra}")

        log.info("=" * 60)
        log.info(f"CHANNEL VALIDATION: {len(passed)}/{len(matrix)} OK")
        if passed:
            log.info(f"✅ Active: {', '.join(passed)}")
        if failed:
            log.error(f"❌ Failed: {', '.join(failed)}")
        log.info("=" * 60)

    async def _validate_channel(self, guild: discord.Guild, tag: str, chan_id: int):
        st = ChannelStatus(channel_id=chan_id, tag=tag)
        channel = guild.get_channel(chan_id)
        st.exists = channel is not None
        if not channel:
            st.last_error = "channel_not_found"
            st.validated_at = datetime.utcnow().isoformat()
            self.ingest_store.upsert_status(st)
            return

        perms = channel.permissions_for(guild.me)
        st.can_read = perms.read_messages
        st.can_history = perms.read_message_history
        st.can_send = perms.send_messages
        st.validated_at = datetime.utcnow().isoformat()

        self.ingest_store.upsert_status(st)

        # Backfill last N messages (env override DISCORD_BACKFILL_N)
        backfill_n = int(os.getenv("DISCORD_BACKFILL_N", "50"))
        if st.can_history:
            try:
                async for msg in channel.history(limit=backfill_n, oldest_first=False):
                    self.ingest_store.record_event(
                        message_id=msg.id,
                        channel_id=chan_id,
                        channel_tag=tag,
                        author=str(msg.author),
                        author_id=msg.author.id,
                        content=msg.content or "",
                        created_at=msg.created_at.replace(tzinfo=None),
                    )
                st.backfill_cursor = str(msg.id) if "msg" in locals() else None
                self.ingest_store.update_status(chan_id, backfill_cursor=st.backfill_cursor)
            except Exception as e:
                st.last_error = f"backfill_error:{e}"
                self.ingest_store.upsert_status(st)

    async def on_ready(self) -> None:
        log.info("Logged in as %s", self.user)

        # Connect DB
        try:
            conn = await self.db.connect()
            if conn:
                await self.db.log_activity(
                    self.settings.org_id,
                    "SYSTEM",
                    f"Bot started: {self.user} connected to {self.settings.dayz_host}",
                    "info",
                )
        except Exception as e:
            log.warning("DB init/connect failed: %s", e)

        # Modular Killfeed is now handled by modules/killfeed/bot.py
        # Legacy KillfeedManager init removed to prevent duplication.

        # Register database log listener
        # [MAXIMUS] Switched to new high-performance regex parser
        from modules.killfeed.parser import ADMParser
        from .log_streamer import get_streamer

        streamer = get_streamer()

        # [CHRONOS] Initialize Live Feed Service
        from .services.live_feed import LiveFeedService
        self.live_feed = LiveFeedService(self)
        try:
            await self.live_feed.start()
            log.info("✅ LiveFeedService started")
        except Exception as e:
            log.error(f"❌ Failed to start LiveFeedService: {e}")

        async def db_log_listener(event):
            if self.db:
                self.db.log_activity(
                    org_id=self.settings.org_id,
                    activity_type=event.level.upper(),
                    message=event.message,
                    severity=event.level if event.level in ("info", "warning", "error") else "info",
                )
                try:
                    # Maximus Parser processes line-by-line
                    event_data = ADMParser.parse_line(event.message)
                    if event_data:
                        # Adapt to list for compatibility if needed, though parse_line is single
                        # For disconnects, we check the type
                        if event_data.get("type") == "disconnect" and "pos_x" in event_data:
                             self.db.update_player_pos(event_data.get("victim"), event_data["pos_x"], event_data.get("pos_y", 0), event_data.get("pos_z", 0))

                        # Hook Processed Killfeed to Ops Spine (LIVE)
                        if event_data.get("type") == "kill":
                            msg = f"💀 **{event_data['killer']}** killed **{event_data['victim']}** with `{event_data['weapon']}`"

                            # Priority 1: Direct Channel (Live Poller mandate)
                            kill_cid = self._tracked_channels().get("killfeed")
                            if kill_cid:
                                chan = self.get_channel(kill_cid)
                                if chan:
                                    try:
                                        await chan.send(msg)
                                    except Exception as e:
                                        log.warning(f"Failed to send to killfeed channel {kill_cid}: {e}")

                            # Priority 2: Webhook Spine (Legacy/Burst)
                            if hasattr(self, "discord_live") and self.discord_live:
                                await self.discord_live.emit_killfeed(msg)

                        elif event_data.get("type") == "hit":
                                # excessive hit logging can be noisy, maybe optional?
                                # adhering to "Live Updates" mandate:
                                pass # hits handled by burst window if enabled, but let's stick to kills for now to avoid overload
                except Exception as ex:
                    log.warning(f"Failed to parse log line for coords: {ex}")

        streamer.add_listener(db_log_listener)

        try:
            await streamer.start()
            log.info("Log streamer started successfully")
        except Exception as e:
            log.error(f"Failed to start log streamer: {e}")


def make_commands(bot: OpsBot) -> None:
    @bot.hybrid_command(name="bot_uptime", description="Show bot uptime")
    async def bot_uptime(ctx: commands.Context) -> None:
        await ctx.send(f"Bot Uptime: {bot.uptime_str}")


def main() -> None:
    # 0. Initialize Observability (Structured Logs + Correlation IDs) ASAP
    from .utils.observability import configure_observability
    configure_observability()

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

    try:
        repo_root = Path(__file__).resolve().parent.parent
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root).decode().strip()
        s.git_sha = sha
    except Exception as exc:
        log.warning("Failed to compute git SHA: %s", exc)
        s.git_sha = "HEAD"

    bot = OpsBot(s)
    make_commands(bot)

    def admin_checker(member):
        return _has_admin_role(member, s.discord_admin_role_ids)

    register_voice_commands(bot, bot.voice_manager, admin_checker)

    from .globals import set_bot
    set_bot(bot)

    from .api import start_api
    import threading

    api_thread = threading.Thread(
        target=start_api,
        kwargs={"host": "0.0.0.0", "port": int(os.getenv("DASHBOARD_PORT", 19101))},
        daemon=True,
    )
    api_thread.start()

    if s.discord_token:
        bot.run(s.discord_token)
    else:
        log.warning("⚠️  DISCORD_TOKEN not set. Running in API-only mode (Docker/Test resilient).")
        import time

        while True:
            time.sleep(3600)


if __name__ == "__main__":
    main()
