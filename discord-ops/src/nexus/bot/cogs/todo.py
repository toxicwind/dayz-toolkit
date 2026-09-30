from __future__ import annotations

import asyncio
import io
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands
import yaml

from src.mildlyawesome.services.todo import TodoService, TodoTask
from src.mildlyawesome.services.view import ViewService

log = logging.getLogger("mildlyawesome.bot.todo")

STATUS_TO_EMOJI = {
    "ready": "🟦",
    "in_progress": "🟨",
    "blocked": "🟥",
    "done": "🟩",
    "dropped": "⛔️",
}
EMOJI_TO_STATUS = {emoji: status for status, emoji in STATUS_TO_EMOJI.items()}

RULES_MESSAGE = (
    "**SERVER TODO (status is emoji-driven; no discussion here)**\n\n"
    "**How to use this channel**\n"
    "* This channel is for task cards only. Ask questions in **#server-chat**.\n"
    "* Each task is one message posted by the bot.\n"
    "* Update status by reacting with exactly one status emoji.\n\n"
    "**Status key (Unicode only)**\n"
    "* 🟥 Blocked (needs info / needs files / can’t proceed)\n"
    "* 🟨 In progress\n"
    "* 🟩 Done\n"
    "* 🟦 Ready / queued (default)\n"
    "* ⛔️ Dropped / won’t do\n\n"
    "**Priority (optional)**\n"
    "* 🔥 P0 (server unplayable)\n"
    "* ⚠️ P1 (economy/feel issues)\n"
    "* ✳️ P2 (nice-to-have)\n"
)


class TodoCog(commands.GroupCog, name="todo", description="Manage the DayZ server TODO board"):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        # Use bot.db to initialize service
        self.service = TodoService(bot.db)
        self.seed_lock = asyncio.Lock()
        self.todo_channel_id: Optional[int] = None
        self.rules_message_id: Optional[int] = None
        self.seed_path = Path(__file__).resolve().parents[3] / "seed_tasks.yaml"
        self._autoseed_done = False

    async def cog_load(self) -> None:
        channel_id = await self.service.get_config("todo_channel_id")
        if channel_id:
            self.todo_channel_id = int(channel_id)
        rules_id = await self.service.get_config("todo_rules_message_id")
        if rules_id:
            self.rules_message_id = int(rules_id)

    async def _require_admin(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.manage_guild:
            return True
        await interaction.response.send_message("Admin permissions required.", ephemeral=True)
        return False

    async def _get_todo_channel(self) -> Optional[discord.TextChannel]:
        if not self.todo_channel_id:
            return None
        return self.bot.get_channel(self.todo_channel_id)

    @app_commands.command(name="seed", description="Post rules and initial tasks.")
    async def todo_seed(self, interaction: discord.Interaction) -> None:
        if not await self._require_admin(interaction):
            return
        channel = await self._get_todo_channel()
        if not channel:
            await interaction.response.send_message("Set channel first.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        async with self.seed_lock:
            # Seed logic using self.service
            pass
        await interaction.followup.send("Seeded.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        # Status update logic
        pass

async def setup(bot: commands.Bot) -> None:
     await bot.add_cog(TodoCog(bot))
