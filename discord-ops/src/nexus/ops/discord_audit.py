import asyncio
import os
import json
import discord
from pathlib import Path
import yaml
from datetime import datetime

# Load settings to get token and guild id
def load_ezstreet_settings():
    repo_root = Path(__file__).resolve().parent.parent
    config_path = repo_root / "config/teams/ezstreet.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)
    
    token = os.getenv("EZSTREET_DISCORD_TOKEN") or data.get("discord", {}).get("token")
    guild_id = data.get("discord", {}).get("guild_id")
    return token, guild_id

async def audit_guild():
    token, guild_id = load_ezstreet_settings()
    if not token or not guild_id:
        print("Missing token or guild_id")
        return

    intents = discord.Intents.default()
    intents.guilds = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        guild = client.get_guild(guild_id)
        if not guild:
            print(f"Guild {guild_id} not found")
            await client.close()
            return

        audit_data = {
            "guild_id": guild.id,
            "guild_name": guild.name,
            "timestamp": datetime.utcnow().isoformat(),
            "categories": [],
            "channels": []
        }

        for category in guild.categories:
            cat_info = {
                "id": category.id,
                "name": category.name,
                "position": category.position,
                "overwrites": []
            }
            # Record overwrites
            for target, overwrites in category.overwrites.items():
                cat_info["overwrites"].append({
                    "target_id": target.id,
                    "target_type": "role" if isinstance(target, discord.Role) else "member",
                    "allow": overwrites.pair()[0].value,
                    "deny": overwrites.pair()[1].value
                })
            audit_data["categories"].append(cat_info)

        for channel in guild.channels:
            chan_info = {
                "id": channel.id,
                "name": channel.name,
                "type": str(channel.type),
                "parent_id": channel.category_id,
                "position": channel.position,
                "overwrites": []
            }
            for target, overwrites in channel.overwrites.items():
                chan_info["overwrites"].append({
                    "target_id": target.id,
                    "target_type": "role" if isinstance(target, discord.Role) else "member",
                    "allow": overwrites.pair()[0].value,
                    "deny": overwrites.pair()[1].value
                })
            audit_data["channels"].append(chan_info)

        # Ensure .chronos/discord directory exists
        repo_root = Path(__file__).resolve().parent.parent
        audit_dir = repo_root / ".chronos/discord"
        audit_dir.mkdir(parents=True, exist_ok=True)
        
        with open(audit_dir / "audit.json", "w") as f:
            json.dump(audit_data, f, indent=2)
        
        print(f"Audit completed: {audit_dir / 'audit.json'}")
        await client.close()

    await client.start(token)

if __name__ == "__main__":
    asyncio.run(audit_guild())
