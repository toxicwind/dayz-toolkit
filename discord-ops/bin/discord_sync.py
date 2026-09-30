import discord
import asyncio
import os
import sys
from pathlib import Path

# Fix path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.mildlyawesome.discord_registry import DiscordRegistry

TOKEN = "MTREDACTED_DISCORD_TOKENeINxdk_s6gw"

class Syncer(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user}")
        guild = self.guilds[0]
        print(f"Syncing Guild: {guild.name}")
        
        repo_root = Path(__file__).resolve().parent.parent
        reg = DiscordRegistry(repo_root)
        
        # Force reload
        reg._reload()
        
        report = await reg.sync(guild, dry_run=False)
        print("Sync Report:", report)
        await self.close()

intents = discord.Intents.default()
intents.guilds = True
client = Syncer(intents=intents)
client.run(TOKEN)

