import discord
from discord.ext import commands
import datetime
import asyncio

class TicketView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="create_ticket_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has open ticket
        # For simplicity, just create one or check channel name collision?
        # Collision check:
        guild = interaction.guild
        cat_id = self.bot.settings.ticket_category_id
        category = guild.get_channel(cat_id) if cat_id else None
        
        chan_name = f"ticket-{interaction.user.name.lower()}"
        existing = discord.utils.get(guild.channels, name=chan_name)
        if existing:
            return await interaction.response.send_message(f"You already have a ticket: {existing.mention}", ephemeral=True)
            
        # Permission overwrites
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Add admin/staff roles
        for rid in self.bot.settings.discord_admin_role_ids:
            role = guild.get_role(rid)
            if role:
                 overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                 
        channel = await guild.create_text_channel(chan_name, category=category, overwrites=overwrites, reason=f"Ticket created by {interaction.user}")
        
        # DB Log
        self.bot.db.create_ticket(str(interaction.user.id), str(channel.id))
        
        # Admin Claim Button (Staff only)
        # Actually Claim button should be in the ticket channel, not the creation panel
        
        embed = discord.Embed(title="Support Ticket", description=f"Hello {interaction.user.mention}, support will be with you shortly.", color=discord.Color.green())
        embed.add_field(name="Controls", value="Use buttons below to manage this ticket.")
        
        view = TicketControlsView(self.bot)
        await channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)

class TicketControlsView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket_btn")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Transcript
        messages = [f"{m.created_at} - {m.author}: {m.content}" async for m in interaction.channel.history(limit=500, oldest_first=True)]
        transcript_text = "\n".join(messages)
        
        # Save to file if long
        file = None
        if len(transcript_text) > 1000:
             import io
             file = discord.File(io.StringIO(transcript_text), filename=f"transcript-{interaction.channel.name}.txt")
             transcript_text = "Transcript attached."
        
        self.bot.db.close_ticket(str(interaction.channel.id), transcript_text)
        
        # Send transcript to logs if configured? For now just close.
        
        await interaction.channel.send("Ticket closing in 5 seconds...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.secondary, emoji="👋", custom_id="claim_ticket_btn")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has admin role
        admin_roles = self.bot.settings.discord_admin_role_ids
        has_role = any(r.id in admin_roles for r in interaction.user.roles)
        # Also check permissions directly
        if not has_role and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Only staff can claim tickets.", ephemeral=True)
            
        await interaction.response.send_message(f"Ticket claimed by {interaction.user.mention}!")
        await interaction.channel.send(f"**Ticket Claimed**\n{interaction.user.mention} will be handling this ticket.")
        
        # Update button to indicate claimed?
        button.label = f"Claimed by {interaction.user.display_name}"
        button.disabled = True
        button.style = discord.ButtonStyle.success
        await interaction.message.edit(view=self)



class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.panel_channel_id = 1452557811497177143

    @commands.hybrid_command(name="ticketpanel", description="Post the support ticket creation panel")
    @commands.has_permissions(administrator=True)
    async def ticketpanel(self, ctx: commands.Context):
        embed = discord.Embed(title="Support Tickets", description="Click the button below to open a ticket.", color=discord.Color.blue())
        await ctx.send(embed=embed, view=TicketView(self.bot))

    @commands.hybrid_command(name="close", description="Close the current support ticket")
    async def close(self, ctx: commands.Context):
        # Fallback command if button fails or user prefers command
        row = self.bot.db.get_ticket(str(ctx.channel.id))
        if not row or row['status'] != 'OPEN':
            return await ctx.send("This is not an open ticket channel.")
            
        messages = [f"{m.created_at} - {m.author}: {m.content}" async for m in ctx.channel.history(limit=500, oldest_first=True)]
        transcript = "\n".join(messages)
        self.bot.db.close_ticket(str(ctx.channel.id), transcript)
        
        await ctx.send("Ticket closing...")
        await asyncio.sleep(5)
        await ctx.channel.delete()
        
    @commands.Cog.listener()
    async def on_ready(self):
        # Register persistent views if needed, for now just relying on dynamic
        self.bot.add_view(TicketView(self.bot))
        self.bot.add_view(TicketControlsView(self.bot))
        
        guild = self.bot.get_guild(self.bot.settings.discord_guild_id)
        if not guild: return

        # Check for ticket panel channel
        channel = guild.get_channel(self.panel_channel_id)
        if channel:
             # Check history to see if panel exists?
             pass
        else:
            print(f"Ticket panel channel {self.panel_channel_id} not found!")

async def setup(bot):
    await bot.add_cog(Tickets(bot))
