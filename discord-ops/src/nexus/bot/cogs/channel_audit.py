from __future__ import annotations

import discord
import logging
from discord.ext import commands
from discord import app_commands

from src.mildlyawesome.services.audit import AuditService
from src.mildlyawesome.services.view import ViewService

log = logging.getLogger("mildlyawesome.bot.audit")

class ChannelAudit(commands.Cog, name="audit"):
    """Recursive channel enumeration and feature mapping."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.service = AuditService()

    @app_commands.command(name="audit", description="Audit all channels and map to bot features")
    @app_commands.checks.has_permissions(administrator=True)
    async def audit_channels(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("Must be run in a guild.", ephemeral=True)
            return

        scan_data = self.service.audit_channels(guild)
        matched_channels = scan_data["matched_channels"]
        unmatched_channels = scan_data["unmatched_channels"]
        
        embed = discord.Embed(title="🔍 Channel Audit Report", color=discord.Color.blue())
        
        matched_text = ""
        for feature, channels in matched_channels.items():
            matched_text += f"**{feature}**: {', '.join(channels[:3])}"
            if len(channels) > 3: matched_text += f", ...(+{len(channels)-3})"
            matched_text += "\n"
            
        embed.add_field(name="✅ Matched Features", value=matched_text[:1024] or "None", inline=False)

        unmatched_text = ""
        for name, cid in unmatched_channels[:10]:
            unmatched_text += f"• #{name} (`{cid}`)\n"
        if len(unmatched_channels) > 10:
            unmatched_text += f"... and {len(unmatched_channels)-10} more"
            
        embed.add_field(name="❓ Unmatched Channels", value=unmatched_text[:1024] or "All matched", inline=False)

        embed.add_field(
            name="💡 Suggestions",
            value=(
                "• Ensure `🟢-status` exists for server board\n"
                "• Ensure `💀-killfeed` exists for combat logs\n"
                "• Ensure `✨-deploy-feed` exists for change track"
            ),
            inline=False
        )
        
        stats = scan_data['stats']
        embed.set_footer(text=f"Total: {stats['total']} | Matched: {stats['matched']} | Unmatched: {stats['unmatched']}")

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ChannelAudit(bot))
