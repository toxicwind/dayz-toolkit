import logging

import discord
from discord.ext import commands

from backend.todo_store import store

log = logging.getLogger("dayz-discord-ops.cogs.todo")


class TodoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await store.initialize()
        log.info("TodoStore initialized")

    @commands.group(invoke_without_command=True)
    async def todo(self, ctx):
        """Todo module commands"""
        await ctx.send("Available commands: add, list, done, drop")

    @todo.command(name="add")
    async def add_task(self, ctx, *, content: str):
        """Add a new task"""
        task_id = await store.add_task(content=content, owner=ctx.author.name)

        # Interactive Message
        msg = await ctx.send(f"✅ **Task #{task_id}** added: {content}\n(React with ✅ to complete, 🗑️ to archive)")
        await msg.add_reaction("✅")
        await msg.add_reaction("🗑️")

        # Link Message to Task
        await store.update_task(task_id, message_id=msg.id, channel_id=msg.channel.id)

    @todo.command(name="archive")
    async def archive_command(self, ctx, task_id: int):
        """Archive a task"""
        success = await store.archive_task(task_id)
        if success:
            await ctx.send(f"📦 Task #{task_id} archived.")
        else:
            await ctx.send(f"❌ Task #{task_id} not found.")

    @todo.command(name="drop")
    async def drop_command(self, ctx, task_id: int):
        """Permanently delete a task"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Only admins can drop tasks.")
            return

        success = await store.drop_task(task_id)
        if success:
            await ctx.send(f"🗑️ Task #{task_id} deleted forever.")
        else:
            await ctx.send(f"❌ Task #{task_id} not found.")

    @todo.command(name="done")
    async def done_command(self, ctx, task_id: int):
        """Mark a task as done"""
        success = await store.update_task(task_id, status="done")
        if success:
            await ctx.send(f"✅ Task #{task_id} marked as DONE.")
        else:
            await ctx.send(f"❌ Task #{task_id} not found.")

    async def list_tasks(self, ctx):
        """List pending tasks"""
        tasks = await store.get_tasks(status="pending")
        if not tasks:
            await ctx.send("No pending tasks.")
            return

        lines = [f"**Pending Tasks ({len(tasks)})**"]
        for t in tasks[:10]:
            lines.append(f"#{t['id']} {t['content']} ({t['priority']})")

        if len(tasks) > 10:
            lines.append(f"...and {len(tasks) - 10} more.")

        await ctx.send("\n".join(lines))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # Ignore bot's own reactions
        if payload.user_id == self.bot.user.id:
            return

        # Find task associated with this message
        task = await store.get_task_by_message_id(payload.message_id)
        if not task:
            return

        # Handle Reactions
        emoji = str(payload.emoji)

        if emoji == "✅":
            # Mark Done
            if task["status"] != "done":
                await store.update_task(task["id"], status="done")
                channel = self.bot.get_channel(payload.channel_id)
                if channel:
                    try:
                        msg = await channel.fetch_message(payload.message_id)
                        await msg.edit(content=f"~~{msg.content}~~ (Completed by <@{payload.user_id}>)")
                    except Exception as e:
                        log.warning(f"Failed to edit message {payload.message_id}: {e}")

        elif emoji == "🗑️":
            # Archive
            await store.archive_task(task["id"])
            channel = self.bot.get_channel(payload.channel_id)
            if channel:
                try:
                    await channel.delete_messages([discord.Object(id=payload.message_id)])
                except Exception as e:
                    log.warning(f"Failed to delete message {payload.message_id}: {e}")


async def setup(bot):
    await bot.add_cog(TodoCog(bot))
