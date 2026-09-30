from __future__ import annotations

import logging
import asyncio
from datetime import datetime, timezone
from collections import deque
from typing import List, Optional, Dict, Any

import discord
from discord.ext import commands, tasks

from src.mildlyawesome.services.view import ViewService
from src.mildlyawesome.core.types import LogEntry, ActivityType

log = logging.getLogger("mildlyawesome.bot.log_intelligence")

class LogIntelligence(commands.Cog):
    """
    Protocol SIGMA: Log Verification and Intelligence Engine.
    Orchestrates ingestion and provides a live audit trail.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.event_store: deque[LogEntry] = deque(maxlen=1000)
        self.sync_loop.start()

    def cog_unload(self):
        self.sync_loop.cancel()

    async def probe(self) -> Dict[str, Any]:
        """Verify connectivity to core services."""
        result = {
            "ftp": {"ok": False, "msg": "Checking..."},
            "db": {"ok": False, "msg": "Checking..."}
        }
        
        try:
            # Probe FTP via bot's service
            files = await self.bot.ftp_service.list_files()
            result["ftp"] = {"ok": True, "files_found": len(files)}
        except Exception as e:
            result["ftp"] = {"ok": False, "msg": str(e)}

        try:
            # Probe DB
            if self.bot.db._conn:
                result["db"] = {"ok": True, "msg": "Connected"}
            else:
                result["db"] = {"ok": False, "msg": "Not Connected"}
        except Exception as e:
            result["db"] = {"ok": False, "msg": str(e)}

        return result

    async def ingest_once(self) -> Dict[str, int]:
        """Hardened ingestion using DayZLogParser."""
        stats = {"events_ingested": 0, "errors": 0}
        try:
            # Ingest via bot's FTP service
            raw_lines = await self.bot.ftp_service.fetch_latest_lines()
            for line in raw_lines:
                parsed = self.bot.log_parser.parse_line(line)
                if parsed:
                    self.event_store.append(parsed)
                    stats["events_ingested"] += 1
            return stats
        except Exception as e:
            log.error(f"Ingest failed: {e}")
            stats["errors"] += 1
            return stats

    @commands.group(name="sigma", invoke_without_command=True)
    async def sigma(self, ctx: commands.Context):
        """Protocol SIGMA Root."""
        await ctx.send_help(ctx.command)

    @sigma.command(name="probe")
    async def sigma_probe(self, ctx: commands.Context):
        """SIGMA-1: Connectivity Check"""
        res = await self.probe()
        msg = "**Protocol SIGMA Probe Results**\n"
        for k, v in res.items():
            icon = "✅" if v['ok'] else "❌"
            msg += f"{icon} **{k.upper()}**: {v.get('msg') or 'OK'}\n"
        await ctx.send(msg)

    @sigma.command(name="sync")
    async def sigma_sync(self, ctx: commands.Context):
        """SIGMA-2: Force Ingestion"""
        msg = await ctx.send("🔄 Running Protocol SIGMA Ingest...")
        stats = await self.ingest_once()
        report = (
            f"**Ingest Complete**\n"
            f"📥 Events Parsed: {stats['events_ingested']}\n"
            f"⚠️ Errors: {stats['errors']}"
        )
        await msg.edit(content=report)

    @sigma.command(name="tail")
    async def sigma_tail(self, ctx: commands.Context, count: int = 10):
        """SIGMA-3: Direct Stream Audit"""
        events = list(self.event_store)[-count:]
        if not events:
            await ctx.send("Buffer empty.")
            return

        lines = ["**Protocol SIGMA: Recent Log Stream**"]
        for e in events:
            lines.append(f"`{e.timestamp}` **{e.activity_type}**: {e.message[:80]}")
        
        await ctx.send("\n".join(lines)[:2000])

    @tasks.loop(minutes=5)
    async def sync_loop(self):
        await self.ingest_once()

    @sync_loop.before_loop
    async def before_sync(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(LogIntelligence(bot))
