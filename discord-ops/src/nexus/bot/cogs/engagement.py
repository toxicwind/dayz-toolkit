from __future__ import annotations

import logging
import discord
from discord.ext import commands
from discord import app_commands

from src.mildlyawesome.services.engagement import EngagementService
from src.mildlyawesome.services.view import ViewService

log = logging.getLogger("mildlyawesome.bot.engagement")

class EngagementCog(commands.Cog, name="engagement"):
    """Tracks survivors activity, streaks, and levels."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.service = EngagementService(bot.db)

    @app_commands.command(name="streak", description="Check your current activity streak and level")
    async def streak(self, interaction: discord.Interaction):
        user = await self.service.get_user(self.bot.settings.org_id, str(interaction.user.id))
        
        embed = discord.Embed(title="🔥 Survivor Standing", color=discord.Color.orange())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        
        embed.add_field(name="Current Streak", value=f"**{user['current_streak']} days**", inline=True)
        embed.add_field(name="Best Streak", value=f"**{user['best_streak']} days**", inline=True)
        embed.add_field(name="Experience (XP)", value=f"**{user['total_xp']:,}**", inline=True)
        embed.add_field(name="Survivor Level", value=f"**Level {user['level']}**", inline=True)
        
        embed.set_footer(text="Keep active to maintain your streak!")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
            
        # Standard XP gain for messages
        result = await self.service.track_activity(self.bot.settings.org_id, str(message.author.id), xp_gain=5)
        
        if result.get('level_up'):
            # Level up celebration
            embed = discord.Embed(
                title="🎊 Level Up!",
                description=f"{message.author.mention} has reached **Level {result['new_level']}**!",
                color=discord.Color.gold()
            )
            await message.channel.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(EngagementCog(bot))
