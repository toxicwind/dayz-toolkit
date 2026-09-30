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

from bot.todo_store import TodoStore, TodoTask

log = logging.getLogger("dayz-discord-ops.todo")

STATUS_TO_EMOJI = {
    "ready": "🟦",
    "in_progress": "🟨",
    "blocked": "🟥",
    "done": "🟩",
    "dropped": "⛔️",
}
EMOJI_TO_STATUS = {emoji: status for status, emoji in STATUS_TO_EMOJI.items()}
PRIORITY_CHOICES = ["P0", "P1", "P2"]
DEFAULT_CATEGORY_ID = 1454365349918277704
DEFAULT_CHANNEL_NAME = "server-todo"

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
    "* ✳️ P2 (nice-to-have)\n\n"
    "**Owner (optional)**\n"
    "* 👤 Tony owns answer / decision\n"
    "* 🧑‍💻 Chris implementing\n\n"
    "**Rule**: If a task is 🟥 Blocked, the next message in #server-chat must answer the blocker."
)


class TodoCog(commands.GroupCog, name="todo", description="Manage the DayZ server TODO board"):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.store = TodoStore()
        self.seed_lock = asyncio.Lock()
        self.todo_channel_id: Optional[int] = None
        self.rules_message_id: Optional[int] = None
        self.seed_path = Path(__file__).resolve().parents[1] / "seed_tasks.yaml"
        self._autoseed_done = False

    async def cog_load(self) -> None:
        await self.store.ensure_ready()
        channel_id = await self.store.get_config("todo_channel_id")
        if channel_id:
            try:
                self.todo_channel_id = int(channel_id)
            except ValueError:
                self.todo_channel_id = None
        rules_id = await self.store.get_config("todo_rules_message_id")
        if rules_id:
            try:
                self.rules_message_id = int(rules_id)
            except ValueError:
                self.rules_message_id = None

    async def _require_admin(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.manage_guild:
            return True
        admin_ids = getattr(self.bot.settings, "discord_admin_role_ids", [])
        if admin_ids:
            member = interaction.guild.get_member(interaction.user.id)
            if member and any(role.id in admin_ids for role in member.roles):
                return True
        await interaction.response.send_message(
            "You need Manage Server or an approved admin role to run this command.",
            ephemeral=True,
        )
        return False

    async def _get_todo_channel(self) -> Optional[discord.TextChannel]:
        if not self.todo_channel_id:
            return None
        channel = self.bot.get_channel(self.todo_channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(self.todo_channel_id)
            except discord.HTTPException:
                return None
        if isinstance(channel, discord.TextChannel):
            return channel
        return None

    async def _fetch_text_channel(self, channel_id: Optional[int]) -> Optional[discord.TextChannel]:
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except discord.HTTPException:
                    channel = None
            if isinstance(channel, discord.TextChannel):
                return channel
            return None
        return await self._get_todo_channel()

    async def _resolve_task_selector(self, selector: Optional[str]) -> Optional[TodoTask]:
        if not selector:
            return None
        task: Optional[TodoTask] = None
        try:
            task_id = int(selector)
            task = await self.store.get_task_by_id(task_id)
        except (TypeError, ValueError):
            task = None
        if task:
            return task
        return await self.store.get_task_by_key(selector)

    async def _refresh_task_message(self, task_id: int) -> None:
        task = await self.store.get_task_by_id(task_id)
        if not task or not task.message_id:
            return
        channel = await self._fetch_text_channel(task.channel_id)
        if not channel:
            return
        try:
            message = await channel.fetch_message(task.message_id)
        except discord.NotFound:
            await self._publish_task_card(channel, task)
            return
        except discord.HTTPException:
            return
        await message.edit(content=self._format_task_message(task))
        await self._apply_status_reaction(message, task.status)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # Auto-seed on first ready so a fresh deploy brings the board up without manual slash usage.
        if self._autoseed_done:
            return
        self._autoseed_done = True
        channel = await self._get_todo_channel()
        if not channel:
            log.info("TODO auto-seed skipped: no channel configured yet.")
            return
        try:
            await self._autoseed_if_needed(channel)
        except Exception as exc:
            log.warning("TODO auto-seed failed: %s", exc)

    @app_commands.command(name="set_channel", description="Set the #server-todo channel that holds task cards.")
    async def todo_set_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        if not await self._require_admin(interaction):
            return
        self.todo_channel_id = channel.id
        await self.store.set_config("todo_channel_id", str(channel.id))
        await interaction.response.send_message(
            f"✅ TODO channel set to {channel.mention}. Seed tasks with `/todo seed`.",
            ephemeral=True,
        )

    @app_commands.command(name="ensure_channel", description="Create #server-todo in the ops category and store it.")
    @app_commands.describe(
        category_id="Discord category ID to place the channel in (defaults to ops category)",
        name="Channel name (default: server-todo)",
    )
    async def todo_ensure_channel(
        self,
        interaction: discord.Interaction,
        category_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> None:
        if not await self._require_admin(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("This command must be run in a guild.", ephemeral=True)
            return
        try:
            cat_id = int(category_id) if category_id else DEFAULT_CATEGORY_ID
        except ValueError:
            await interaction.followup.send("Category ID must be an integer.", ephemeral=True)
            return
        category = guild.get_channel(cat_id)
        if category is None:
            try:
                category = await self.bot.fetch_channel(cat_id)
            except discord.HTTPException:
                category = None
        if not isinstance(category, discord.CategoryChannel):
            await interaction.followup.send(
                f"Category {cat_id} not found; please provide a valid category id.", ephemeral=True
            )
            return
        channel_name = (name or DEFAULT_CHANNEL_NAME).replace(" ", "-").lower()
        existing = discord.utils.get(category.text_channels, name=channel_name)
        if existing:
            self.todo_channel_id = existing.id
            await self.store.set_config("todo_channel_id", str(existing.id))
            await interaction.followup.send(
                f"Channel already exists: {existing.mention}. Stored as TODO channel.",
                ephemeral=True,
            )
            return
        try:
            created = await guild.create_text_channel(
                channel_name,
                category=category,
                reason="Ensure TODO channel exists",
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "Missing Manage Channels permission to create the TODO channel.", ephemeral=True
            )
            return
        except discord.HTTPException as exc:
            await interaction.followup.send(
                f"Failed to create channel: {exc}", ephemeral=True
            )
            return
        self.todo_channel_id = created.id
        await self.store.set_config("todo_channel_id", str(created.id))
        await interaction.followup.send(
            f"Created {created.mention} in {category.name} and stored as TODO channel. Run `/todo seed` next.",
            ephemeral=True,
        )

    @app_commands.command(name="seed", description="Post the pinned rules + initial tasks from seed_tasks.yaml.")
    @app_commands.describe(force_rules="Repost the rules message even if one exists already.")
    async def todo_seed(self, interaction: discord.Interaction, force_rules: bool = False) -> None:
        if not await self._require_admin(interaction):
            return
        channel = await self._get_todo_channel()
        if not channel:
            await interaction.response.send_message(
                "Configure a channel first with `/todo set_channel`.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        async with self.seed_lock:
            rules_created = await self._post_rules_message(channel, force=force_rules)
            try:
                seeded = await self._seed_tasks(channel)
            except FileNotFoundError as exc:
                await interaction.followup.send(str(exc), ephemeral=True)
                return
        status_text = "reposted" if rules_created else "verified"
        await interaction.followup.send(
            f"Rules {status_text}. Seeded {seeded} new cards from `seed_tasks.yaml`.",
            ephemeral=True,
        )

    async def _post_rules_message(self, channel: discord.TextChannel, force: bool = False) -> bool:
        if self.rules_message_id and not force:
            try:
                await channel.fetch_message(self.rules_message_id)
                return False
            except discord.NotFound:
                pass
        message = await channel.send(RULES_MESSAGE)
        try:
            await message.pin()
        except discord.Forbidden:
            log.warning("Missing permission to pin TODO rules message.")
        self.rules_message_id = message.id
        await self.store.set_config("todo_rules_message_id", str(message.id))
        return True

    async def _seed_tasks(self, channel: discord.TextChannel) -> int:
        if not self.seed_path.exists():
            raise FileNotFoundError(f"Missing seed file at {self.seed_path}")
        with self.seed_path.open("r", encoding="utf-8") as fp:
            payload = yaml.safe_load(fp) or {}
        tasks = payload.get("tasks", [])
        created = 0
        for task_data in tasks:
            normalized = {
                "task_key": task_data.get("key"),
                "title": task_data["title"],
                "scope": task_data["scope"],
                "surface": task_data["surface"],
                "acceptance": task_data["acceptance"],
                "owner": task_data.get("owner") or None,
                "priority": task_data.get("priority", "P1"),
                "status": task_data.get("status", "ready"),
            }
            todo_task = await self.store.upsert_task_from_seed(normalized)
            if not todo_task.message_id:
                await self._publish_task_card(channel, todo_task)
                created += 1
        return created

    async def _autoseed_if_needed(self, channel: discord.TextChannel) -> None:
        # Seed only when rules or any task messages are missing; idempotent.
        async with self.seed_lock:
            need_rules = False
            if self.rules_message_id:
                try:
                    await channel.fetch_message(self.rules_message_id)
                except discord.NotFound:
                    need_rules = True
            else:
                need_rules = True

            tasks = await self.store.list_tasks(include_archived=True)
            missing_cards = not tasks or any(t.message_id is None for t in tasks)

            if not need_rules and not missing_cards:
                return

            if need_rules:
                await self._post_rules_message(channel, force=True)
            if missing_cards:
                await self._seed_tasks(channel)

    async def _task_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        del interaction  # unused for now
        term = (current or "").lower()
        tasks = await self.store.list_tasks()
        choices: List[app_commands.Choice[str]] = []
        for task in tasks:
            label = f"{STATUS_TO_EMOJI.get(task.status, '🟦')} [{task.priority}] {task.title}"
            search_blob = f"{task.title} {task.task_key or ''}".lower()
            if term and term not in search_blob:
                continue
            choices.append(app_commands.Choice(name=label[:100], value=str(task.id)))
            if len(choices) >= 25:
                break
        return choices

    def _format_task_message(self, task: TodoTask) -> str:
        emoji = STATUS_TO_EMOJI.get(task.status, "🟦")
        owner_line = f"Owner: {task.owner}" if task.owner else "Owner: —"
        ref_line = f"Ref: {task.task_key or f'task-{task.id}'}"
        return "\n".join(
            [
                f"{emoji} [{task.priority}] {task.title}",
                f"Scope: {task.scope}",
                f"Surface: {task.surface}",
                f"Acceptance: {task.acceptance}",
                owner_line,
                ref_line,
            ]
        )

    async def _publish_task_card(self, channel: discord.TextChannel, task: TodoTask) -> None:
        message = await channel.send(self._format_task_message(task))
        await self.store.set_task_message(task.id, channel.id, message.id)
        await self._apply_status_reaction(message, task.status)

    async def _apply_status_reaction(self, message: discord.Message, status: str) -> None:
        for reaction in message.reactions:
            emoji_str = str(reaction.emoji)
            if emoji_str not in EMOJI_TO_STATUS:
                continue
            try:
                await message.clear_reaction(reaction.emoji)
            except (discord.Forbidden, discord.HTTPException):
                # As a fallback try to remove per-user reactions.
                try:
                    async for user in reaction.users(limit=None):
                        if user == self.bot.user:
                            continue
                        await message.remove_reaction(reaction.emoji, user)
                except discord.HTTPException:
                    pass
        emoji = STATUS_TO_EMOJI.get(status)
        if emoji:
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException:
                pass

    @app_commands.command(name="add", description="Create a new TODO task card.")
    @app_commands.describe(
        title="Card title",
        scope="One sentence scope or outcome",
        surface="Files/systems to touch",
        acceptance="Observable validation/result",
        priority="Priority bucket (P0/P1/P2)",
        owner="Optional owner tag to display",
    )
    @app_commands.choices(
        priority=[
            app_commands.Choice(name="P0 (🔥 blocker)", value="P0"),
            app_commands.Choice(name="P1 (⚠️ economy)", value="P1"),
            app_commands.Choice(name="P2 (✳️ nice-to-have)", value="P2"),
        ]
    )
    async def todo_add(
        self,
        interaction: discord.Interaction,
        title: str,
        scope: str,
        surface: str,
        acceptance: str,
        priority: Optional[app_commands.Choice[str]] = None,
        owner: Optional[str] = None,
    ) -> None:
        if not await self._require_admin(interaction):
            return
        channel = await self._get_todo_channel()
        if not channel:
            await interaction.response.send_message(
                "Set a TODO channel first with `/todo set_channel`.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        task = await self.store.insert_task(
            {
                "task_key": None,
                "title": title,
                "scope": scope,
                "surface": surface,
                "acceptance": acceptance,
                "owner": owner,
                "priority": priority.value if priority else "P1",
                "status": "ready",
            }
        )
        await self._publish_task_card(channel, task)
        await interaction.followup.send(
            f"Posted `{task.title}` to {channel.mention}.", ephemeral=True
        )

    @app_commands.command(name="owner", description="Assign or clear an owner on a TODO card.")
    @app_commands.describe(task="Task title/key (autocomplete) or numeric ID", owner="Optional owner label; leave blank to clear")
    async def todo_owner(
        self, interaction: discord.Interaction, task: str, owner: Optional[str] = None
    ) -> None:
        if not await self._require_admin(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        todo_task = await self._resolve_task_selector(task)
        if not todo_task:
            await interaction.followup.send("Task not found.", ephemeral=True)
            return
        owner_value = owner.strip() if owner else None
        await self.store.update_task_owner(todo_task.id, owner_value)
        await self._refresh_task_message(todo_task.id)
        label = owner_value or "—"
        await interaction.followup.send(
            f"Owner for `{todo_task.title}` set to `{label}`.",
            ephemeral=True,
        )

    @todo_owner.autocomplete("task")
    async def todo_owner_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self._task_autocomplete(interaction, current)

    @app_commands.command(name="priority", description="Update card priority (P0/P1/P2).")
    @app_commands.describe(task="Task title/key (autocomplete) or numeric ID")
    @app_commands.choices(
        priority=[
            app_commands.Choice(name="P0 (🔥 blocker)", value="P0"),
            app_commands.Choice(name="P1 (⚠️ economy)", value="P1"),
            app_commands.Choice(name="P2 (✳️ nice-to-have)", value="P2"),
        ]
    )
    async def todo_priority(
        self,
        interaction: discord.Interaction,
        task: str,
        priority: app_commands.Choice[str],
    ) -> None:
        if not await self._require_admin(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        todo_task = await self._resolve_task_selector(task)
        if not todo_task:
            await interaction.followup.send("Task not found.", ephemeral=True)
            return
        await self.store.update_task_priority(todo_task.id, priority.value)
        await self._refresh_task_message(todo_task.id)
        await interaction.followup.send(
            f"`{todo_task.title}` priority set to {priority.value}.",
            ephemeral=True,
        )

    @todo_priority.autocomplete("task")
    async def todo_priority_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self._task_autocomplete(interaction, current)

    @app_commands.command(name="status", description="Manually set a task status without using reactions.")
    @app_commands.describe(task="Task title/key (autocomplete) or numeric ID")
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Ready", value="ready"),
            app_commands.Choice(name="In Progress", value="in_progress"),
            app_commands.Choice(name="Blocked", value="blocked"),
            app_commands.Choice(name="Done", value="done"),
            app_commands.Choice(name="Dropped", value="dropped"),
        ]
    )
    async def todo_status(
        self,
        interaction: discord.Interaction,
        task: str,
        status: app_commands.Choice[str],
    ) -> None:
        if not await self._require_admin(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        todo_task = await self._resolve_task_selector(task)
        if not todo_task:
            await interaction.followup.send("Task not found.", ephemeral=True)
            return
        await self.store.update_task_status(todo_task.id, status.value)
        await self._refresh_task_message(todo_task.id)
        await interaction.followup.send(
            f"`{todo_task.title}` marked as {status.name}.", ephemeral=True
        )

    @todo_status.autocomplete("task")
    async def todo_status_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self._task_autocomplete(interaction, current)

    @app_commands.command(name="list", description="List TODO cards with optional filters.")
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Ready", value="ready"),
            app_commands.Choice(name="In Progress", value="in_progress"),
            app_commands.Choice(name="Blocked", value="blocked"),
            app_commands.Choice(name="Done", value="done"),
            app_commands.Choice(name="Dropped", value="dropped"),
        ],
        priority=[
            app_commands.Choice(name="P0", value="P0"),
            app_commands.Choice(name="P1", value="P1"),
            app_commands.Choice(name="P2", value="P2"),
        ],
    )
    async def todo_list(
        self,
        interaction: discord.Interaction,
        status: Optional[app_commands.Choice[str]] = None,
        priority: Optional[app_commands.Choice[str]] = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=False)
        tasks = await self.store.list_tasks(
            status=status.value if status else None,
            priority=priority.value if priority else None,
        )
        if not tasks:
            await interaction.followup.send("No tasks match that filter.", ephemeral=True)
            return
        guild_id = interaction.guild_id or self.bot.settings.discord_guild_id
        lines: List[str] = []
        for task in tasks:
            url = (
                f"https://discord.com/channels/{guild_id}/{task.channel_id}/{task.message_id}"
                if task.channel_id and task.message_id
                else "(no message)"
            )
            lines.append(
                f"{STATUS_TO_EMOJI.get(task.status, '🟦')} [{task.priority}] "
                f"[{task.title}]({url})"
            )
        await interaction.followup.send("\n".join(lines[:50]), ephemeral=True)

    @app_commands.command(name="info", description="Show the full task card details + jump link.")
    @app_commands.describe(task="Task title/key (autocomplete) or numeric ID")
    async def todo_info(self, interaction: discord.Interaction, task: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=False)
        todo_task = await self._resolve_task_selector(task)
        if not todo_task:
            await interaction.followup.send("Task not found.", ephemeral=True)
            return
        guild_id = interaction.guild_id or self.bot.settings.discord_guild_id
        url = (
            f"https://discord.com/channels/{guild_id}/{todo_task.channel_id}/{todo_task.message_id}"
            if todo_task.channel_id and todo_task.message_id
            else None
        )
        lines = [
            f"{STATUS_TO_EMOJI.get(todo_task.status, '🟦')} [{todo_task.priority}] {todo_task.title}",
            f"Owner: {todo_task.owner or '—'}",
            f"Scope: {todo_task.scope}",
            f"Surface: {todo_task.surface}",
            f"Acceptance: {todo_task.acceptance}",
            f"Ref: {todo_task.task_key or f'task-{todo_task.id}'}",
        ]
        if url:
            lines.append(f"Message: {url}")
        await interaction.followup.send("\n".join(lines), ephemeral=True)

    @todo_info.autocomplete("task")
    async def todo_info_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return await self._task_autocomplete(interaction, current)

    @app_commands.command(name="export", description="Export all tasks (including archived) as YAML.")
    async def todo_export(self, interaction: discord.Interaction) -> None:
        if not await self._require_admin(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        tasks = await self.store.list_tasks(include_archived=True)
        export_payload: Dict[str, object] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tasks": [
                {
                    "id": task.id,
                    "key": task.task_key,
                    "title": task.title,
                    "scope": task.scope,
                    "surface": task.surface,
                    "acceptance": task.acceptance,
                    "owner": task.owner,
                    "priority": task.priority,
                    "status": task.status,
                    "archived": task.archived,
                    "channel_id": task.channel_id,
                    "message_id": task.message_id,
                }
                for task in tasks
            ],
        }
        stream = io.StringIO()
        yaml.safe_dump(export_payload, stream, sort_keys=False)
        stream.seek(0)
        await interaction.followup.send(
            "Here is the current TODO export.",
            file=discord.File(fp=stream, filename="todo_export.yaml"),
            ephemeral=True,
        )

    @app_commands.command(name="archive_done", description="Archive and delete cards that are marked as done.")
    async def todo_archive_done(self, interaction: discord.Interaction) -> None:
        if not await self._require_admin(interaction):
            return
        channel = await self._get_todo_channel()
        if not channel:
            await interaction.response.send_message(
                "Set a TODO channel first via `/todo set_channel`.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        tasks = await self.store.list_tasks(status="done")
        archived_ids: List[int] = []
        for task in tasks:
            if task.message_id:
                try:
                    msg = await channel.fetch_message(task.message_id)
                    await msg.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    log.warning("Missing Manage Messages permission to delete task %s", task.id)
            await self.store.delete_task_message(task.id)
            archived_ids.append(task.id)
        await self.store.archive_tasks(archived_ids)
        await interaction.followup.send(
            f"Archived {len(archived_ids)} completed tasks.", ephemeral=True
        )

    @app_commands.command(name="repair", description="Recreate missing cards or message links.")
    async def todo_repair(self, interaction: discord.Interaction) -> None:
        if not await self._require_admin(interaction):
            return
        channel = await self._get_todo_channel()
        if not channel:
            await interaction.response.send_message(
                "Set a TODO channel first via `/todo set_channel`.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        tasks = await self.store.list_tasks()
        repaired = 0
        for task in tasks:
            if not task.message_id:
                await self._publish_task_card(channel, task)
                repaired += 1
                continue
            try:
                await channel.fetch_message(task.message_id)
            except discord.NotFound:
                await self._publish_task_card(channel, task)
                repaired += 1
        await interaction.followup.send(
            f"Repaired {repaired} missing cards.", ephemeral=True
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.user_id == (self.bot.user.id if self.bot.user else 0):
            return
        if str(payload.emoji) not in EMOJI_TO_STATUS:
            return
        if self.todo_channel_id and payload.channel_id != self.todo_channel_id:
            return
        task = await self.store.get_task_by_message(payload.message_id)
        if not task or task.archived:
            return

        new_status = EMOJI_TO_STATUS[str(payload.emoji)]
        await self.store.update_task_status(task.id, new_status)
        updated = await self.store.get_task_by_id(task.id)
        if not updated:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(payload.channel_id)
            except discord.HTTPException:
                return
        if not isinstance(channel, discord.TextChannel):
            return
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            await self._publish_task_card(channel, updated)
            return
        await message.edit(content=self._format_task_message(updated))
        await self._apply_status_reaction(message, new_status)

        user = payload.member or getattr(payload, "user", None)
        if not user:
            try:
                user = await self.bot.fetch_user(payload.user_id)
            except discord.HTTPException:
                user = None
        log.info(
            "TODO status change: task_id=%s status=%s actor=%s",
            task.id,
            new_status,
            getattr(user, "display_name", payload.user_id),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TodoCog(bot))
