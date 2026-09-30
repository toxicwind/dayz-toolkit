import asyncio
import os
import discord
from pathlib import Path
import yaml
import logging

# Minimal config loader
def load_token_from_defaults():
    repo_root = Path(__file__).parent.parent
    config_path = repo_root / "config/teams/ezstreet.yaml"
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f)
            return data.get("discord", {}).get("token")
    return os.getenv("DISCORD_TOKEN")

TARGET_CATEGORY_ID = 1454365349918277704

async def audit_target_category():
    token = load_token_from_defaults()
    if not token:
        print("ERROR: No token found")
        return

    intents = discord.Intents.default()
    intents.guilds = True
    
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        
        found = False
        target_cat = None
        
        # Search all guilds
        for guild in client.guilds:
            cat = guild.get_channel(TARGET_CATEGORY_ID)
            if cat:
                target_cat = cat
                print(f"✅ Found Category in Guild: {guild.name} ({guild.id})")
                break
        
        if not target_cat:
            print(f"❌ Category {TARGET_CATEGORY_ID} NOT FOUND in any accessible guild.")
            await client.close()
            return

        print(f"\nAUDIT REPORT FOR CATEGORY: {target_cat.name} ({target_cat.id})")
        print("="*60)
        
        # Verify type
        if not isinstance(target_cat, discord.CategoryChannel):
            print(f"❌ ERROR: ID points to {type(target_cat)}, not a CategoryChannel!")
            await client.close()
            return

        channels = sorted(target_cat.channels, key=lambda c: c.position)
        
        if not channels:
            print("(Category is Empty)")
        
        for i, channel in enumerate(channels):
            print(f"#{i} [{channel.type}] {channel.name} (ID: {channel.id})")
            print(f"    Topic: {channel.topic}")
        
        print("="*60)
        await client.close()

    await client.start(token)

if __name__ == "__main__":
    asyncio.run(audit_target_category())
