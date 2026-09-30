import logging

from discord.ext import commands

from backend.engagement_store import store

log = logging.getLogger("dayz-discord-ops.cogs.engagement")


class EngagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await store.initialize()
        log.info("EngagementStore initialized")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        # Dummy point logic for activity
        await store.add_points(message.author.id, message.author.name, "message", 1)

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        """Show top survivors"""
        rows = await store.get_leaderboard(5)
        if not rows:
            await ctx.send("No engagement data yet.")
            return

        lines = ["**🏆 Engagement Leaderboard**"]
        for i, row in enumerate(rows, 1):
            lines.append(f"{i}. {row['user_name']} - {row['total_points']} pts ({row['rank_tier']})")

        await ctx.send("\n".join(lines))


async def setup(bot):
    await bot.add_cog(EngagementCog(bot))
