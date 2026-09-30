from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any

import discord
from discord import app_commands
from discord.ext import commands

from src.mildlyawesome.services.trader import TraderService, TraderItem
from src.mildlyawesome.services.view import ViewService
from src.mildlyawesome.services.spawn_manager import SpawnManager

log = logging.getLogger("mildlyawesome.bot.trader")

class TraderCog(commands.GroupCog, name="trader", description="Server Side Item Shop"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        # Service initialized in setup_hook or here
        csv_path = "server/ezstreet/trader_items_with_classnames.csv"
        self.service = TraderService(bot.db, self.bot.spawn_manager, csv_path)

    @app_commands.command(name="search", description="Search the trader catalog")
    async def trader_search(self, interaction: discord.Interaction, query: str):
        items = self.service.search_items(query)
        if not items:
            await interaction.response.send_message("No items found matching that query.", ephemeral=True)
            return

        embed = discord.Embed(title=f"🔍 Trader Search: {query}", color=discord.Color.blue())
        for item in items:
            embed.add_field(
                name=item.name, 
                value=f"Price: `{item.price:,.0f} credits`\nClass: `{item.classname}`",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="buy", description="Purchase an item for your next spawn")
    async def trader_buy(self, interaction: discord.Interaction, item_name: str):
        # Implementation of buy logic
        # 1. Search for EXACT or best match
        items = self.service.search_items(item_name)
        if not items:
            await interaction.response.send_message("Item not found.", ephemeral=True)
            return
        
        item = items[0] # Take first match for simplicity in this hardened version
        
        # 2. Get player gamertag (we need a way to link Discord ID to Gamertag)
        user_data = await self.bot.db.get_user_data(self.bot.settings.org_id, str(interaction.user.id))
        if not user_data or not user_data.get('gamertag'):
            await interaction.response.send_message("You must link your gamertag first!", ephemeral=True)
            return
        
        gamertag = user_data['gamertag']
        
        # 3. Get player location (last known from logs)
        # For now, we'll use a default or require player to have been logged recently
        if not user_data.get('last_pos_x'):
             await interaction.response.send_message("Last known location unknown. Please login and logout once.", ephemeral=True)
             return
             
        pos = (user_data['last_pos_x'], user_data['last_pos_y'], user_data['last_pos_z'])
        
        result = await self.service.purchase_item(
            self.bot.settings.org_id, str(interaction.user.id), 
            gamertag, item, pos
        )
        
        if result['success']:
            await interaction.response.send_message(
                f"✅ **Purchase Successful!**\n"
                f"Item: `{item.name}`\n"
                f"Cost: `{item.price:,.0f} credits`\n"
                f"Remaining: `{result['new_balance']:,.0f} credits`\n\n"
                f"*Item will spawn at your last logout position after the next server restart.*",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(f"❌ **Purchase Failed**: {result['error']}", ephemeral=True)

async def setup(bot: commands.Bot):
    # Ensure spawn_manager is on bot
    if not hasattr(bot, 'spawn_manager'):
        bot.spawn_manager = SpawnManager()
    await bot.add_cog(TraderCog(bot))
