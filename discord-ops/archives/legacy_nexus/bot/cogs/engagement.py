import discord
from discord.ext import commands
from discord import app_commands
from ..engagement import init_engagement_manager, get_engagement_manager

class EngagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.manager = init_engagement_manager(bot.db)

    @commands.hybrid_command(name="streak", description="Check your current daily activity streak")
    async def streak(self, ctx: commands.Context):
        manager = get_engagement_manager()
        if not manager:
            return await ctx.send("Engagement manager not initialized.", ephemeral=True)
            
        user_id = str(ctx.author.id)
        engagement = await manager._get_or_create_user(user_id)
        
        embed = discord.Embed(title="🔥 Activity Streak", color=discord.Color.orange())
        embed.add_field(name="Current Streak", value=f"{engagement.current_streak} days", inline=True)
        embed.add_field(name="Best Streak", value=f"{engagement.best_streak} days", inline=True)
        embed.add_field(name="Total XP", value=f"{engagement.total_xp:,}", inline=True)
        embed.add_field(name="Level", value=f"{engagement.level}", inline=True)
        
        await ctx.send(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
            
        manager = get_engagement_manager()
        if manager:
            result = await manager.track_message(str(message.author.id))
            if result.get('level_up'):
                await message.channel.send(f"🎊 {message.author.mention} leveled up to **Level {result['new_level']}**!")

async def setup(bot):
    await bot.add_cog(EngagementCog(bot))
