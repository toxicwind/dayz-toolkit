import discord
import os
import asyncio

token = os.getenv("DISCORD_TOKEN")
guild_id = 1418315612005994650
target_category_id = 1454365349918277704

intents = discord.Intents.default()
intents.guilds = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    guild = client.get_guild(guild_id)
    if not guild:
         print("Guild not found")
         await client.close()
         return

    print(f"Checking categories in {guild.name}...")
    found = False
    for cat in guild.categories:
        print(f" - {cat.name} (ID: {cat.id})")
        if cat.id == target_category_id:
            found = True

    if found:
        print(f"\nTarget Category {target_category_id} FOUND!")
    else:
        print(f"\nTarget Category {target_category_id} NOT FOUND.")

    await client.close()

client.run(token)
