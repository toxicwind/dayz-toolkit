import asyncio
import logging
import os
import sys
from pathlib import Path
import yaml

# Path setup
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.mildlyawesome.discord_registry import DiscordRegistry
import discord

# Setup Logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("reconstitute")

def load_token():
    # Try global config
    token = os.getenv("DISCORD_TOKEN")
    if token:
        return token
        
    # Try ezstreet config fallback
    config_path = repo_root / "config/teams/ezstreet.yaml"
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f)
            return data.get("discord", {}).get("token")
    return None

async def main():
    token = load_token()
    if not token:
        log.error("No Discord Token Found")
        sys.exit(1)

    registry = DiscordRegistry(repo_root)
    
    intents = discord.Intents.default()
    intents.guilds = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        log.info(f"Logged in as {client.user}")
        
        # Assume single guild for now or find from config
        # For this task we might default to the one found in config or iterator
        # ezstreet guild_id: 1418315612005994650
        
        # We need to find the guild that contains the target category
        target_cat = registry.spec.get("target_category_id")
        
        guild = None
        for g in client.guilds:
             # Check if this guild has the category? 
             # Actually, simpler to just use the configured guild ID if available
             pass
        
        # Just use first guild for safety/simple in this context or from ezstreet.yaml
        # But let's look for the category
        for g in client.guilds:
            if g.get_channel(int(target_cat)):
                guild = g
                break
        
        if not guild:
            log.error(f"Could not find guild with category {target_cat}")
            # Fallback to ezstreet guild ID for creation if category missing?
            # Start loop
            pass

        if guild:
            log.info(f"Syncing guild: {guild.name}")
            report = await registry.sync(guild, dry_run=False)
            log.info("Sync Report:")
            for k, v in report.items():
                log.info(f"  {k}: {v}")
        
        await client.close()

    await client.start(token)

if __name__ == "__main__":
    asyncio.run(main())
