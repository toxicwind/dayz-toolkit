import asyncio
import os
import sys
from pathlib import Path

# Add repo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import load_settings
import discord

async def send_test_messages():
    settings = load_settings()
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        try:
            print(f"Logged in as {client.user}")
            
            channels = {
                "〖🟢〗 Server Status": settings.discord.status_channel_id,
                "〖💀〗 Kill Feed": settings.discord.killfeed_channel_id,
                "〖🪦〗 Death Feed": settings.discord.deathfeed_channel_id,
                "〖✨〗 Deploy Feed": settings.discord.changefeed_channel_id
            }
            
            for name, cid in channels.items():
                if not cid:
                    print(f"Skipping {name} (ID missing)")
                    continue
                
                channel = client.get_channel(cid)
                if not channel:
                    try:
                        channel = await client.fetch_channel(cid)
                    except Exception as e:
                        print(f"Failed to fetch {name} ({cid}): {e}")
                        continue
                
                if channel:
                    try:
                        emoji = name.split()[0]
                        clean_name = " ".join(name.split()[1:])
                        await channel.send(
                            f"**RESTORED DIAGNOSTIC**\n"
                            f"**{emoji} {clean_name} matched successfully.**\n"
                            f"〖`SYSTEM_OK`〗 〖📍 `INTERNAL_AUDIT`〗\n"
                            f"{client.user.mention} is now routing events to this channel with full aesthetic support."
                        )
                        print(f"Sent aesthetic test message to {name}")
                    except Exception as e:
                        print(f"Failed to send to {name}: {e}")
            
            await client.close()
        except Exception as e:
            print(f"CRITICAL ERROR in on_ready: {e}")
            await client.close()

    if not settings.discord.token:
        # Final fallback override
        settings.discord.token = os.getenv("DISCORD_TOKEN", "")

    if not settings.discord.token:
        print("Error: DISCORD_TOKEN not found in environment or config.")
        return

    await client.start(settings.discord.token)

if __name__ == "__main__":
    asyncio.run(send_test_messages())
