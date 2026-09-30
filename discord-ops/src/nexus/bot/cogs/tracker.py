from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
import logging

from src.mildlyawesome.services.identity import IdentityService

log = logging.getLogger("mildlyawesome.bot.tracker")

class TrackerCog(commands.Cog, name="tracker"):
    """Player identity tracking and gamertag linking."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.service = IdentityService(bot.db)

    @app_commands.command(name="whois", description="Lookup a player's identity across the server")
    @app_commands.checks.has_permissions(administrator=True)
    async def whois(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True)
        
        results = await self.service.whois(self.bot.settings.org_id, query)
        if not results:
            await interaction.followup.send(f"No survivors found matching `{query}`.", ephemeral=True)
            return

        embed = discord.Embed(title="🕵️ Survivor Identity Report", color=discord.Color.blue())
        for res in results[:5]: # Top 5 results
            embed.add_field(
                name=res.get('last_known_name', 'Unknown'),
                value=f"ID: `{res.get('player_id')}`\nLast Seen: {res.get('last_seen')}",
                inline=False
            )
        
        if len(results) > 5:
            embed.set_footer(text=f"... and {len(results)-5} more matches.")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="register", description="Link your Discord account to your DayZ Gamertag")
    async def register(self, interaction: discord.Interaction, gamertag: str):
        success = await self.service.link_gamertag(self.bot.settings.org_id, str(interaction.user.id), gamertag)
        if success:
            await interaction.response.send_message(
                f"✅ **Registration Successful!**\nLinked {interaction.user.mention} to gamertag: `{gamertag}`",
                ephemeral=False
            )
        else:
            await interaction.response.send_message("❌ Registration failed. System error.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(TrackerCog(bot))
