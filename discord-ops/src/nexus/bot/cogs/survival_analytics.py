from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
import logging

from src.mildlyawesome.services.analytics import AnalyticsEngine

log = logging.getLogger("mildlyawesome.bot.analytics")

class SurvivalAnalyticsCog(commands.Cog, name="analytics"):
    """Server Performance and Survivor Intelligence."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Using the engine already on the bot if it exists, or creating one
        if not hasattr(bot, 'analytics_engine'):
            bot.analytics_engine = AnalyticsEngine(bot.db)
        self.engine = bot.analytics_engine

    @app_commands.command(name="stats", description="Check player survival statistics and threat level")
    async def stats(self, interaction: discord.Interaction, player_name: str = None):
        await interaction.response.defer()
        
        search_name = player_name
        if not search_name:
            user_data = await self.bot.db.get_user_data(self.bot.settings.org_id, str(interaction.user.id))
            if user_data and user_data.get('gamertag'):
                search_name = user_data['gamertag']
            else:
                await interaction.followup.send("Please provide a name or link your gamertag first.", ephemeral=True)
                return

        profile = await self.engine.get_player_survival_profile(self.bot.settings.org_id, search_name)
        if not profile:
            await interaction.followup.send(f"No survivor records found for `{search_name}`.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📊 Survivor Intelligence: {profile['name']}",
            color=discord.Color.dark_green()
        )
        
        embed.add_field(name="Standing", value=f"**{profile['pattern']}**", inline=True)
        embed.add_field(name="Threat", value=f"**{profile['threat']}**", inline=True)
        embed.add_field(name="Score", value=f"**{profile['score']}/100**", inline=True)
        
        embed.add_field(name="Combat", value=f"Kills: `{profile['kills']}`\nDeaths: `{profile['deaths']}`\nK/D: `{profile['kd']}`", inline=False)
        
        if profile.get('last_seen'):
            embed.set_footer(text=f"Last Seen: {profile['last_seen']}")

        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(SurvivalAnalyticsCog(bot))
