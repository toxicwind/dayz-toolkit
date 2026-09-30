import asyncio
import logging
import discord
from discord.ext import commands, tasks
from mildlyawesome.a2s_query import query_info
from mildlyawesome.config import load_settings

log = logging.getLogger("mildlyawesome.modules.stats")

class StatChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = load_settings()
        # Start the loop
        self.update_stats_loop.start()

    def cog_unload(self):
        self.update_stats_loop.cancel()

    @tasks.loop(minutes=5)
    async def update_stats_loop(self):
        """Periodically update the statistics channels."""
        await self.bot.wait_until_ready()

        try:
            guild = self.bot.get_guild(self.settings.discord_guild_id)
            if not guild:
                log.warning("Guild not found, skipping stats update.")
                return

            # 1. Server Stats (A2S)
            server_str = "🎮 Server: Offline"
            try:
                # Use query_info from a2s_query
                # We need host/port. settings has dayz_host/dayz_query_port?
                full_host = self.settings.dayz_host
                # dayz_host usually ip:port. a2s needs separate.
                if ":" in full_host:
                    host_ip, host_port = full_host.split(":")
                    host_port = int(host_port)
                else:
                    host_ip = full_host
                    host_port = 2302 # Default or from settings.dayz_port

                # Check if query port is different
                query_port = getattr(self.settings, "dayz_query_port", host_port)

                info = await asyncio.to_thread(query_info, host_ip, query_port)
                server_str = f"🎮 Server: {info.players}/{info.max_players}"
            except Exception as e:
                log.error(f"A2S Query failed: {e}")

            # 2. Discord Members
            # Count total and online
            total_members = guild.member_count
            online_members = sum(1 for m in guild.members if m.status != discord.Status.offline)

            # 3. Resolve Channels
            registry = getattr(self.bot, "registry", None)
            if not registry:
                log.warning("Bot registry not available.")
                return

            chan_map = {
                "ops.stats_server": server_str,
                "ops.stats_online": f"👥 Online: {online_members}",
                "ops.stats_members": f"📈 Members: {total_members}"
            }

            for key, name in chan_map.items():
                cid = registry.resolve(key)
                if not cid:
                    continue

                channel = guild.get_channel(cid)
                if channel and channel.name != name:
                    try:
                        await channel.edit(name=name)
                        log.info(f"Updated {key} -> {name}")
                        # Rate limit protection
                        await asyncio.sleep(1.0)
                    except Exception as e:
                        log.error(f"Failed to update {key}: {e}")

        except Exception as e:
            log.error(f"Error in update_stats_loop: {e}")

    @commands.command(name="force_stats")
    @commands.is_owner()
    async def force_stats(self, ctx):
        """Force update stat channels."""
        await ctx.send("Forcing stats update...")
        await self.update_stats_loop()
        await ctx.send("Stats update triggered.")

    @update_stats_loop.before_loop
    async def before_update_stats_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(StatChannels(bot))
