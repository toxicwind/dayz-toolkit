import discord
from discord.ext import commands, tasks
from ..tracker import PlayerTracker
from ..tracking_db import Database as TrackingDB
import os

class TrackerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        db_path = os.getenv("PLAYER_TRACKER_DB", "player_tracker.db")
        self.tracking_db = TrackingDB(db_path)
        self.tracker = PlayerTracker(
            bot.settings.dayz_host,
            bot.db,
        )
        self.scan_loop.start()

    def cog_unload(self):
        self.scan_loop.cancel()

    @tasks.loop(minutes=5.0)
    async def scan_loop(self):
        try:
            # Run blocking scan in thread
            await self.bot.loop.run_in_executor(None, self.tracker.scan_and_update)
        except Exception as e:
            print(f"Tracker scan failed: {e}")

    @commands.hybrid_command(name="whois", description="Check a player's real name or alias")
    async def whois(self, ctx: commands.Context, search: str):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("Admin only.", ephemeral=True)

        # Search by name or alias
        players = self.tracking_db.get_all_players()
        match = None
        for p in players:
            if search.lower() in p.get('real_name', '').lower() or \
               (p.get('fake_name') and search.lower() in p['fake_name'].lower()) or \
               search == p.get('steam_id'):
                match = p
                break
        
        if match:
            embed = discord.Embed(title="🕵️ Player Identity", color=discord.Color.blue())
            embed.add_field(name="Real Name", value=match.get('real_name', 'Unknown'))
            embed.add_field(name="Alias (Fake Name)", value=match.get('fake_name', 'None'))
            embed.add_field(name="Steam/Console ID", value=f"`{match.get('steam_id')}`")
            await ctx.send(embed=embed, ephemeral=True)
        else:
            await ctx.send("Player not found.", ephemeral=True)

    @scan_loop.before_loop
    async def before_scan(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(TrackerCog(bot))
