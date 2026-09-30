
import os
import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('DISCORD_GUILD_ID'))

intents = discord.Intents.default()
# intents.members = True # If needed

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print(f"Could not find guild with ID {GUILD_ID}")
        await bot.close()
        return

    me = guild.me
    print(f"Permissions for {bot.user} in guild '{guild.name}':")
    
    critical_perms = [
        ('manage_channels', 'Manage Channels'),
        ('manage_roles', 'Manage Roles'),
        ('view_channel', 'View Channels'),
        ('connect', 'Connect'),
        ('speak', 'Speak')
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
        
    await bot.close()

if __name__ == '__main__':
    print("Starting Permission Check...")
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Error running bot: {e}")
