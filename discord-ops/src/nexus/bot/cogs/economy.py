from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any

import discord
from discord import app_commands
from discord.ext import commands

from src.mildlyawesome.services.economy import EconomyService
from src.mildlyawesome.services.view import ViewService

log = logging.getLogger("mildlyawesome.bot.economy")

class EconomyCog(commands.GroupCog, name="economy", description="Server Banking and Credits"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.service = EconomyService(bot.db)

    @app_commands.command(name="balance", description="Check your credit balance")
    async def eco_balance(self, interaction: discord.Interaction):
        balance = await self.service.get_balance(self.bot.settings.org_id, str(interaction.user.id))
        
        embed = discord.Embed(
            title="💳 Personal Bank Account",
            description=f"Current Balance: **{balance:,.0f} credits**",
            color=0x2ecc71 # Green
        )
        embed.set_footer(text=f"User ID: {interaction.user.id}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="transfer", description="Transfer credits to another survivor")
    async def eco_transfer(self, interaction: discord.Interaction, target: discord.Member, amount: float):
        if amount <= 0:
            await interaction.response.send_message("Amount must be positive.", ephemeral=True)
            return
            
        success = await self.service.transfer(
            self.bot.settings.org_id, str(interaction.user.id), str(target.id), amount
        )
        
        if success:
            await interaction.response.send_message(
                f"✅ Transferred `{amount:,.0f} credits` to {target.mention}.",
                ephemeral=False
            )
        else:
            await interaction.response.send_message("❌ Transfer failed. Insufficient funds or system error.", ephemeral=True)

    @app_commands.command(name="history", description="View your recent transaction history")
    async def eco_history(self, interaction: discord.Interaction):
        history = await self.service.get_history(self.bot.settings.org_id, str(interaction.user.id))
        if not history:
            await interaction.response.send_message("No recent transactions found.", ephemeral=True)
            return
            
        embed = discord.Embed(title="📜 Transaction History", color=discord.Color.blue())
        for tx in history:
            tx_type = "🟢" if tx['cost'] > 0 else "🔴"
            embed.add_field(
                name=f"{tx_type} {tx['item_name']}",
                value=f"Amount: `{tx['cost']:,.0f}`\nDate: {tx['timestamp']}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))
