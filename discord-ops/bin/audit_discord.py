#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
from pathlib import Path

# Fix path to allow imports from src
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.mildlyawesome.config import load_settings
from src.mildlyawesome.discord_registry import DiscordRegistry
import discord

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("auditor")

class AuditClient(discord.Client):
    def __init__(self, registry: DiscordRegistry, guild_id: int):
        intents = discord.Intents.default()
        intents.guilds = True
        super().__init__(intents=intents)
        self.registry = registry
        self.target_guild_id = guild_id
        self.done = asyncio.Event()

    async def on_ready(self):
        log.info(f"Audit Bot Connected: {self.user}")
        guild = self.get_guild(self.target_guild_id)
        if not guild:
            log.error(f"Guild {self.target_guild_id} not found")
            await self.close()
            return

        await self.generate_audit(guild)
        await self.close()

    async def generate_audit(self, guild: discord.Guild):
        lines = []
        lines.append(f"# DISCORD AUDIT REPORT")
        lines.append(f"**Date:** {discord.utils.utcnow().isoformat()}")
        lines.append(f"**Guild:** {guild.name} ({guild.id})")
        
        lines.append(f"\n## 1. Registry State (Mappings)")
        assignments = self.registry.state.get("assignments", {})
        lines.append("| Logical Key | Mapped ID | Found on Guild? | Category Correct? |")
        lines.append("|---|---|---|---|")
        
        for key, cid in assignments.items():
            chan = guild.get_channel(int(cid))
            found = "✅" if chan else "❌"
            cat_ok = "UNKNOWN"
            if chan:
                cat_ok = "✅" if chan.category_id == self.registry.target_category_id else f"❌ ({chan.category_id})"
            
            lines.append(f"| `{key}` | `{cid}` | {found} | {cat_ok} |")

        lines.append(f"\n## 2. Live Channel Scan (Ops Category)")
        target_cat = guild.get_channel(self.registry.target_category_id)
        if target_cat and isinstance(target_cat, discord.CategoryChannel):
            lines.append(f"**Category:** {target_cat.name} ({target_cat.id})")
            lines.append("| Position | Name | ID | Type | Webhooks |")
            lines.append("|---|---|---|---|---|")
            for channel in sorted(target_cat.channels, key=lambda x: x.position):
                wh_str = "N/A"
                if isinstance(channel, (discord.TextChannel, discord.ForumChannel)):
                    try:
                        webhooks = await channel.webhooks()
                        wh_str = ", ".join([w.name for w in webhooks]) if webhooks else "None"
                    except Exception:
                        wh_str = "ERR"
                lines.append(f"| {channel.position} | {channel.name} | {channel.id} | {channel.type} | {wh_str} |")
        else:
            lines.append(f"❌ **Private Category {self.registry.target_category_id} NOT FOUND**")

        lines.append(f"\n## 3. Legacy Locks Check")
        # Check channels that look like they are locked
        locked_found = []
        for c in guild.channels:
            if c.name.startswith("🔒-"):
                locked_found.append(c)
        
        if locked_found:
             lines.append("| Name | ID | Category |")
             lines.append("|---|---|---|")
             for c in locked_found:
                 cat_name = c.category.name if c.category else "None"
                 lines.append(f"| {c.name} | {c.id} | {cat_name} |")
        else:
            lines.append("No channels with lock prefix `🔒-` found.")

        # Write to file
        with open("DISCORD_AUDIT.md", "w") as f:
            f.write("\n".join(lines))
        
        log.info("DISCORD_AUDIT.md generated.")

async def main():
    settings = load_settings()
    repo_root = Path(__file__).resolve().parent.parent
    registry = DiscordRegistry(repo_root)
    
    if not settings.discord_token:
        log.error("No Discord Token")
        sys.exit(1)
        
    client = AuditClient(registry, settings.discord_guild_id)
    try:
        async with client:
            await client.start(settings.discord_token)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    if os.name == "posix":
        import stat
        st = os.stat(__file__)
        os.chmod(__file__, st.st_mode | stat.S_IEXEC)
    asyncio.run(main())
