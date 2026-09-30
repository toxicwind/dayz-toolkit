import discord
from discord.ext import commands
from ..survival_analytics import calculate_survival_score, determine_activity_pattern, determine_threat_level
from ..tracking_db import Database as TrackingDB
import os

class SurvivalAnalyticsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        db_path = os.getenv("PLAYER_TRACKER_DB", "player_tracker.db")
        self.tracking_db = TrackingDB(db_path)

    @commands.hybrid_command(name="stats", description="Check player survival statistics")
    async def stats(self, ctx: commands.Context, player_name: str = None):
        # Default to self if registered
        search_name = player_name
        if not search_name:
            # Try to get registered gamertag
            user_data = self.bot.db.get_user_data(self.bot.settings.org_id, str(ctx.author.id))
            if user_data:
                search_name = user_data['gamertag']
            else:
                return await ctx.send("Please provide a player name or `/register` your gamertag.", ephemeral=True)

        # Lookup in tracking DB
        players = self.tracking_db.get_all_players()
        match = None
        for p in players:
            if search_name.lower() in p.get('real_name', '').lower() or \
               (p.get('fake_name') and search_name.lower() in p['fake_name'].lower()):
                match = p
                break
        
        if not match:
            return await ctx.send(f"Player '{search_name}' not found in tracking records.", ephemeral=True)

        steam_id = match['steam_id']
        stats = self.tracking_db.get_player_stats(steam_id)
        
        kills = stats.get('kills', 0)
        deaths = max(stats.get('deaths', 1), 1)
        kd_ratio = round(kills / deaths, 2)
        playtime = stats.get('playtime_hours', 0)
        
        score = calculate_survival_score(kills, deaths, playtime)
        pattern = determine_activity_pattern(kills, deaths, playtime)
        threat = determine_threat_level(kills, kd_ratio, score)
        
        embed = discord.Embed(title=f"📊 Survival Profile: {match.get('fake_name') or match.get('real_name')}", color=discord.Color.green())
        embed.add_field(name="Survival Score", value=f"**{score}** / 100", inline=True)
        embed.add_field(name="Threat Level", value=threat.upper(), inline=True)
        embed.add_field(name="Pattern", value=pattern.capitalize(), inline=True)
        
        embed.add_field(name="Kills", value=str(kills), inline=True)
        embed.add_field(name="Deaths", value=str(deaths), inline=True)
        embed.add_field(name="K/D Ratio", value=str(kd_ratio), inline=True)
        
        embed.add_field(name="Playtime", value=f"{playtime:.1f} hours", inline=True)
        embed.add_field(name="Fav Weapon", value=stats.get('favorite_weapon', 'Unknown'), inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SurvivalAnalyticsCog(bot))
