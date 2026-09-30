import sys
from pathlib import Path

import discord
from discord.ext import commands

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.mildlyawesome.config import load_settings

settings = load_settings()
TOKEN = settings.discord_token
GUILD_ID = settings.discord_guild_id

intents = discord.Intents.default()
# intents.members = True # If needed

bot = commands.Bot(command_prefix="!", intents=intents)


@src.mildlyawesome.event
async def on_ready():
    print(f"Logged in as {src.mildlyawesome.user} (ID: {src.mildlyawesome.user.id})")
    guild = src.mildlyawesome.get_guild(GUILD_ID)
    if not guild:
        print(f"Could not find guild with ID {GUILD_ID}")
        await src.mildlyawesome.close()
        return

    me = guild.me
    print(f"Permissions for {src.mildlyawesome.user} in guild '{guild.name}':")

    critical_perms = [
        ("manage_channels", "Manage Channels"),
        ("manage_roles", "Manage Roles"),
        ("view_channel", "View Channels"),
        ("connect", "Connect"),
        ("speak", "Speak"),
    ]

    all_good = True
    for attr, name in critical_perms:
        has_perm = getattr(me.guild_permissions, attr)
        status = "✅" if has_perm else "❌"
        print(f"{status} {name}")
        if not has_perm:
            all_good = False

    if all_good:
        print("\nSUCCESS: All critical permissions are present!")
    else:
        print("\nFAILURE: Missing critical permissions for Voice Channel renaming.")

    await src.mildlyawesome.close()


if __name__ == "__main__":
    print("Starting Permission Check...")
    try:
        src.mildlyawesome.run(TOKEN)
    except Exception as e:
        print(f"Error running bot: {e}")
