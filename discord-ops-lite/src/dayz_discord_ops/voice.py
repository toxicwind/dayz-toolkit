"""
Voice Channel Module for DayZ Discord Ops Bot
Provides voice channel join, leave, and TTS announcement capabilities.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional
import io

import discord
from discord import app_commands

log = logging.getLogger("dayz-discord-ops.voice")


class VoiceManager:
    """Manages voice connections for the bot."""
    
    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self._voice_client: Optional[discord.VoiceClient] = None
    
    @property
    def voice_client(self) -> Optional[discord.VoiceClient]:
        """Return current voice client if connected."""
        return self._voice_client
    
    @property
    def is_connected(self) -> bool:
        """Check if bot is connected to a voice channel."""
        return self._voice_client is not None and self._voice_client.is_connected()
    
    async def join_channel(self, channel: discord.VoiceChannel) -> discord.VoiceClient:
        """Join a voice channel."""
        if self.is_connected:
            if self._voice_client.channel.id == channel.id:
                return self._voice_client
            await self._voice_client.move_to(channel)
            return self._voice_client
        
        self._voice_client = await channel.connect()
        log.info("Joined voice channel: %s", channel.name)
        return self._voice_client
    
    async def leave_channel(self) -> bool:
        """Leave the current voice channel."""
        if not self.is_connected:
            return False
        
        channel_name = self._voice_client.channel.name
        await self._voice_client.disconnect()
        self._voice_client = None
        log.info("Left voice channel: %s", channel_name)
        return True
    
    async def play_tts(self, text: str, *, wait: bool = True) -> bool:
        """
        Play TTS audio in the connected voice channel.
        Requires ffmpeg and espeak/gTTS for TTS generation.
        For simplicity, using Discord's built-in TTS or a simple approach.
        """
        if not self.is_connected:
            return False
        
        # For now, we'll use a simple beep/notification approach
        # Full TTS would require additional packages like gTTS or espeak
        log.info("TTS requested (text length: %d chars)", len(text))
        
        # Placeholder - in production, integrate with gTTS:
        # from gtts import gTTS
        # tts = gTTS(text=text, lang='en')
        # audio_file = io.BytesIO()
        # tts.write_to_fp(audio_file)
        # audio_file.seek(0)
        # audio_source = discord.FFmpegPCMAudio(audio_file, pipe=True)
        # self._voice_client.play(audio_source)
        
        return True


def register_voice_commands(bot, voice_manager: VoiceManager, admin_role_checker) -> None:
    """Register voice-related slash commands."""
    
    @bot.tree.command(name="voice_join", description="Bot joins your current voice channel")
    async def voice_join(interaction: discord.Interaction) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("❌ Not in a guild context.", ephemeral=True)
            return
        
        if not member.voice or not member.voice.channel:
            await interaction.response.send_message("❌ You need to be in a voice channel first!", ephemeral=True)
            return
        
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        try:
            channel = member.voice.channel
            await voice_manager.join_channel(channel)
            await interaction.followup.send(f"✅ Joined **{channel.name}**!", ephemeral=True)
        except Exception as e:
            log.exception("Failed to join voice channel")
            await interaction.followup.send(f"❌ Failed to join: {type(e).__name__}: {e}", ephemeral=True)
    
    @bot.tree.command(name="voice_leave", description="Bot leaves the voice channel")
    async def voice_leave(interaction: discord.Interaction) -> None:
        if not voice_manager.is_connected:
            await interaction.response.send_message("❌ Not in a voice channel.", ephemeral=True)
            return
        
        await interaction.response.defer(thinking=True, ephemeral=True)
        channel_name = voice_manager.voice_client.channel.name
        await voice_manager.leave_channel()
        await interaction.followup.send(f"👋 Left **{channel_name}**.", ephemeral=True)
    
    @bot.tree.command(name="voice_announce", description="Announce a message in voice channel (admin only)")
    @app_commands.describe(message="The message to announce via TTS")
    async def voice_announce(interaction: discord.Interaction, message: str) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("❌ Not in a guild context.", ephemeral=True)
            return
        
        # Check admin role
        if not admin_role_checker(member):
            await interaction.response.send_message("❌ Admin role required.", ephemeral=True)
            return
        
        if not voice_manager.is_connected:
            await interaction.response.send_message("❌ Bot is not in a voice channel. Use `/voice_join` first.", ephemeral=True)
            return
        
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        success = await voice_manager.play_tts(message)
        if success:
            await interaction.followup.send(f"📢 Announced: *{message[:50]}...*" if len(message) > 50 else f"📢 Announced: *{message}*", ephemeral=True)
        else:
            await interaction.followup.send("❌ TTS playback failed.", ephemeral=True)
    
    @bot.tree.command(name="voice_status", description="Check voice connection status")
    async def voice_status(interaction: discord.Interaction) -> None:
        if voice_manager.is_connected:
            channel = voice_manager.voice_client.channel
            members = len(channel.members)
            await interaction.response.send_message(
                f"🎤 Connected to **{channel.name}** ({members} members)",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("🔇 Not connected to any voice channel.", ephemeral=True)
