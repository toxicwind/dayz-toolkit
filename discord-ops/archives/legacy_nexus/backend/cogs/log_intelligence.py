import asyncio
import logging
import os
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from ftplib import FTP
from pathlib import Path
from typing import Any

from discord.ext import commands, tasks

from backend.config import load_settings

logger = logging.getLogger(__name__)


@dataclass
class EZStreetEvent:
    """Standardized Event Object for Protocol SIGMA"""

    timestamp: str  # UTC ISO
    event_type: str  # CHAT, KILL, ADM, SYSTEM
    source: str  # ftp:file.ADM, api:log
    raw: str  # Original line
    player: str | None = None
    target: str | None = None

    def to_dict(self):
        return asdict(self)


class LogIntelligence(commands.Cog):
    """
    Protocol SIGMA: Log Verification Engine.
    Responsibilities:
    1. PROBE: Verify connectivity.
    2. INGEST: Pull and parse logs.
    3. SERVE: Expose normalized events.
    """

    def __init__(self, bot):
        self.bot = bot
        self.settings = load_settings()

        # Store
        self.event_store = deque(maxlen=1000)  # In-memory buffer for SIGMA Verification

        # Config
        self.local_log_dir = Path("/app/logs")
        self.local_log_dir.mkdir(exist_ok=True, parents=True)

        self.ftp_host = os.getenv("DAYZ_FTP_HOST", "usla352.gamedata.io")
        self.ftp_user = os.getenv("DAYZ_FTP_USER", "ni12435433_1")
        self.ftp_pass = os.getenv("DAYZ_FTP_PASS", "")

        # State
        self.last_sync_stats = {}

        # Start background sync (keep it alive, but SIGMA focuses on verification)
        self.sync_loop.start()

    def cog_unload(self):
        self.sync_loop.cancel()

    # --- LAYER 1: PROBE ---
    async def probe(self) -> dict[str, Any]:
        """Check availability of external sources (FTP/API)"""
        result = {"ftp": {"ok": False, "msg": "Not checked"}, "api": {"ok": False, "msg": "Not configured"}}

        try:
            # Lightweight check: List root
            files = await asyncio.to_thread(self.bot.ftp_service.client.list_files, self.bot.settings.ftp_base_path)
            result["ftp"] = {"ok": True, "files": [f["name"] for f in files[:5]]}
        except Exception as e:
            result["ftp"] = {"ok": False, "msg": str(e)}

        return result

    # --- LAYER 2: INGEST ---
    async def ingest_once(self) -> dict[str, int]:
        """Trigger a manual sync and parsing run."""
        stats = {"ftp_files": 0, "ftp_events": 0, "api_events": 0, "errors": 0}

        try:
            events = await self.bot.ftp_service.ingest_logs()
            stats["ftp_events"] = len(events)
            # FTPService handles file selection internally
            stats["ftp_files"] = 2  # ADM and RPT
            self.last_sync_stats = stats
            return stats
        except Exception as e:
            logger.error(f"Ingest failed: {e}")
            stats["errors"] += 1
            return stats

    def _download_if_new(self, ftp: FTP, filename: str) -> bool:
        local_path = self.local_log_dir / filename
        try:
            remote_size = ftp.size(filename)
        except:
            remote_size = 0

        if local_path.exists():
            if local_path.stat().st_size == remote_size and remote_size > 0:
                return False

        with open(local_path, "wb") as f:
            ftp.retrbinary(f"RETR {filename}", f.write)
        return True

    def _parse_local_file(self, filename: str, stats: dict):
        """Parse file into EZStreetEvents"""
        path = self.local_log_dir / filename
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.strip():
                    continue

                # SIGMA PARSER: Keep it stupid simple for now
                event = EZStreetEvent(
                    timestamp=datetime.utcnow().isoformat(),
                    event_type="LOG",
                    source=f"ftp:{filename}",
                    raw=line.strip(),
                    player=None,
                )

                # Basic classification
                if " Chat" in line:
                    event.event_type = "CHAT"
                elif "hit by" in line or "killed by" in line:
                    event.event_type = "COMBAT"
                elif "connected" in line:
                    event.event_type = "LOGIN"

                self.event_store.append(event)
                stats["ftp_events"] += 1

    # --- LAYER 3: SERVE ---
    def get_recent_events(self, limit: int = 50) -> list[dict]:
        """Return raw event stream"""
        return [e.to_dict() for e in list(self.event_store)[-limit:]]

    # --- DISCORD COMMANDS ---
    @commands.group(invoke_without_command=True)
    async def logs(self, ctx):
        await ctx.send_help(ctx.command)

    @logs.command(name="probe")
    async def logs_probe(self, ctx):
        """SIGMA-1: Connectivity Check"""
        res = await self.probe()

        msg = "**Protocol SIGMA Probe Results**\n"

        ftp = res["ftp"]
        icon = "✅" if ftp["ok"] else "❌"
        msg += f"{icon} **FTP**: {ftp.get('msg') or 'OK'}\n"
        if ftp.get("files"):
            msg += f"   files: {', '.join(ftp['files'][:3])}...\n"

        api = res["api"]
        icon = "✅" if api["ok"] else "❌"
        msg += f"{icon} **API**: {api.get('msg') or 'OK'}\n"

        await ctx.send(msg)

    @logs.command(name="sync")
    async def logs_sync(self, ctx):
        """SIGMA-2: Force Ingestion"""
        msg = await ctx.send("🔄 Running Protocol SIGMA Ingest...")
        stats = await self.ingest_once()

        report = (
            f"**Ingest Complete**\n"
            f"📂 Files Scanned: {stats['ftp_files']}\n"
            f"📥 Events Parsed: {stats['ftp_events']}\n"
            f"⚠️ Errors: {stats['errors']}"
        )
        await msg.edit(content=report)

    @logs.command(name="tail")
    async def logs_tail(self, ctx, count: int = 10):
        """SIGMA-3: View Verification"""
        events = self.get_recent_events(limit=count)
        if not events:
            await ctx.send("buffer empty.")
            return

        lines = ["**Log Tail**"]
        for e in events:
            lines.append(f"`{e['timestamp']}` **{e['event_type']}**: {e['raw'][:80]}")

        await ctx.send("\n".join(lines)[:2000])

    @tasks.loop(minutes=5)
    async def sync_loop(self):
        # Keep background sync alive for dashboard
        await self.ingest_once()

    @sync_loop.before_loop
    async def before_sync(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(LogIntelligence(bot))
