"""
Channel Audit Tool - Recursive channel enumeration and feature mapping
"""
import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

log = logging.getLogger("dayz-discord-ops.audit")

# Known bot feature -> channel name patterns
CHANNEL_FEATURE_MAP = {
    "status_board": ["status", "server-status", "🟢"],
    "killfeed": ["killfeed", "kill-feed", "combat", "💀"],
    "changefeed": ["deploy", "changes", "feed", "✨"],
    "connections": ["connections", "server-connections"],
    "selfplay": ["selfplay", "🧪"],
    "trader": ["trader", "shop", "market", "💰"],
    "tickets": ["ticket", "support", "🎫"],
    "casino": ["casino", "gambling", "🎰"],
    "bank": ["bank", "economy", "💵"],
    "leaderboard": ["leaderboard", "stats", "🏆"],
    "announcements": ["announce", "news", "📢"],
    "logs": ["logs", "audit", "📋"],
    "voice": ["voice", "🔊"],
    "welcome": ["welcome", "rules", "👋"],
}

@dataclass
class ChannelAuditResult:
    channel_id: int
    channel_name: str
    channel_type: str
    category: Optional[str]
    matched_feature: Optional[str]
    suggestions: List[str]

class ChannelAudit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="audit_channels", description="Audit all channels and map to bot features")
    @app_commands.checks.has_permissions(administrator=True)
    async def audit_channels(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            await interaction.followup.send("Must be run in a guild.", ephemeral=True)
            return

    def scan_guild(self, guild: discord.Guild) -> dict:
        results: List[ChannelAuditResult] = []
        matched_channels: Dict[str, List[str]] = {}
        unmatched_channels: List[Tuple[str, int]] = []

        for channel in guild.channels:
            channel_name_lower = channel.name.lower()
            category_name = channel.category.name if channel.category else "No Category"

            # Determine channel type
            if isinstance(channel, discord.TextChannel):
                ch_type = "text"
            elif isinstance(channel, discord.VoiceChannel):
                ch_type = "voice"
            elif isinstance(channel, discord.CategoryChannel):
                ch_type = "category"
            elif isinstance(channel, discord.ForumChannel):
                ch_type = "forum"
            elif isinstance(channel, discord.StageChannel):
                ch_type = "stage"
            else:
                ch_type = "unknown"

            # Match against known features
            matched_feature = None
            for feature, patterns in CHANNEL_FEATURE_MAP.items():
                for pattern in patterns:
                    if pattern.lower() in channel_name_lower:
                        matched_feature = feature
                        if feature not in matched_channels:
                            matched_channels[feature] = []
                        matched_channels[feature].append(f"#{channel.name}")
                        break
                if matched_feature:
                    break

            # Generate suggestions for unmatched text channels
            suggestions = []
            if not matched_feature and ch_type == "text":
                unmatched_channels.append((channel.name, channel.id))
                # Heuristic suggestions based on name
                if "general" in channel_name_lower:
                    suggestions.append("Could be used for bot announcements")
                elif "admin" in channel_name_lower:
                    suggestions.append("Could be used for admin logs/alerts")
                elif "bot" in channel_name_lower:
                    suggestions.append("Dedicated bot channel - consider all features")
                else:
                    suggestions.append("No automatic mapping - manual review needed")

            results.append(ChannelAuditResult(
                channel_id=channel.id,
                channel_name=channel.name,
                channel_type=ch_type,
                category=category_name,
                matched_feature=matched_feature,
                suggestions=suggestions
            ))

        return {
            "results": results,
            "matched_channels": matched_channels,
            "unmatched_channels": unmatched_channels,
            "stats": {
                "total": len(guild.channels),
                "matched": sum(len(v) for v in matched_channels.values()),
                "unmatched": len(unmatched_channels)
            }
        }

    @app_commands.command(name="audit_channels", description="Audit all channels and map to bot features")
    @app_commands.checks.has_permissions(administrator=True)
    async def audit_channels(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            await interaction.followup.send("Must be run in a guild.", ephemeral=True)
            return

        scan_data = self.scan_guild(guild)
        matched_channels = scan_data["matched_channels"]
        unmatched_channels = scan_data["unmatched_channels"]
        results = scan_data["results"]

        # Build report embed
        embed = discord.Embed(
            title="🔍 Channel Audit Report",
            color=discord.Color.blue()
        )

        # Matched features
        matched_text = ""
        for feature, channels in matched_channels.items():
            matched_text += f"**{feature}**: {', '.join(channels)}\n"
        if matched_text:
            embed.add_field(name="✅ Matched Features", value=matched_text[:1024], inline=False)
        else:
            embed.add_field(name="✅ Matched Features", value="None found", inline=False)

        # Unmatched channels
        unmatched_text = ""
        for name, cid in unmatched_channels[:15]:  # Limit to 15
            unmatched_text += f"• #{name} (`{cid}`)\n"
        if len(unmatched_channels) > 15:
            unmatched_text += f"... and {len(unmatched_channels) - 15} more"
        if unmatched_text:
            embed.add_field(name="❓ Unmatched Channels", value=unmatched_text[:1024], inline=False)
        else:
            embed.add_field(name="❓ Unmatched Channels", value="All channels matched!", inline=False)

        # Suggestions
        embed.add_field(
            name="💡 Suggestions",
            value=(
                "• Create `🟢-status` for server status\n"
                "• Create `💀-killfeed` for combat events\n"
                "• Create `✨-deploy-feed` for change notifications\n"
                "• Create `🎰-casino` for gambling games\n"
                "• Create `🎫-tickets` for support tickets"
            ),
            inline=False
        )

        embed.set_footer(text=f"Total: {scan_data['stats']['total']} | Matched: {scan_data['stats']['matched']} | Unmatched: {scan_data['stats']['unmatched']}")

        await interaction.followup.send(embed=embed, ephemeral=True)

        # Also log full results
        log.info(f"Channel Audit Complete: {len(results)} channels scanned")
        for r in results:
            if r.matched_feature:
                log.info(f"  MATCHED: #{r.channel_name} -> {r.matched_feature}")
            elif r.channel_type == "text":
                log.info(f"  UNMATCHED: #{r.channel_name} ({r.channel_id})")

async def setup(bot):
    await bot.add_cog(ChannelAudit(bot))
