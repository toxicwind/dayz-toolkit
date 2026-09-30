"""
Discord Live Updates Module
Autonomous webhook-based system for real-time server event broadcasting.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

import aiohttp
import discord

if TYPE_CHECKING:
    from .bot import OpsBot

log = logging.getLogger("dayz-discord-ops.live_updates")


class LiveUpdateSystem:
    """Manages autonomous Discord channel updates via webhooks."""

    def __init__(self, bot: OpsBot):
        self.bot = bot
        self.webhooks: dict[str, discord.Webhook] = {}
        self.last_player_count = 0
        self.server_status_message_id: int | None = None
        self._spawned = False

    async def setup(self):
        """Initialize webhooks and start background tasks."""
        await self.setup_webhooks()

        # Subscribe to Event Bus
        bus = self.bot.event_bus
        bus.subscribe("killfeed.kill", self.push_killfeed_event)
        bus.subscribe("admin.action", self.push_admin_event)
        bus.subscribe("loot.event", self.push_loot_event_bus)
        bus.subscribe("patch.applied", self.push_patch_announcement)

        if not self._spawned:
            await self.bot.supervisor.spawn("server_status_update", self._server_status_loop)
            self._spawned = True
            log.info("[LIVE_UPDATES] Spawned supervised server status loop")

    async def push_killfeed_event(self, payload: dict):
        await self.push_killfeed(payload)

    async def push_admin_event(self, payload: dict):
        await self.push_admin_action(payload)

    async def push_loot_event_bus(self, payload: dict):
        await self.push_loot_event(payload)

    async def push_patch_announcement(self, payload: dict):
        """Handle patch announcements."""
        if "changelog" not in self.webhooks:
            return
        try:
            embed = discord.Embed(
                title=f"🚀 Patch Deployed: {payload.get('title', 'Unknown Patch')}",
                description=payload.get("description", "No details provided."),
                color=discord.Color.brand_green(),
                timestamp=datetime.utcnow(),
            )
            embed.set_author(name="Ops Team", icon_url="https://i.imgur.com/8u1bZjX.png")  # Placeholder

            changes = payload.get("changes", [])
            if changes:
                # Format changes into a list
                change_list = "\n".join([f"• {c}" for c in changes[:10]])  # Limit to 10
                if len(changes) > 10:
                    change_list += f"\n*...and {len(changes) - 10} more*"
                embed.add_field(name="Changelog", value=change_list, inline=False)

            embed.set_footer(text=f"Version: {payload.get('version', 'N/A')}")

            await self.robust_send("changelog", embed, "Patch Bot")
        except Exception as e:
            log.error(f"[LIVE_UPDATES] Patch announcement error: {e}")

    async def setup_webhooks(self):
        """Create or retrieve webhooks for each target channel."""
        await self.bot.wait_until_ready()
        settings = self.bot.settings.discord

        channel_map = {
            "killfeed": getattr(settings, "killfeed_channel_id", None),
            "admin_log": getattr(settings, "admin_log_channel_id", None),
            "server_status": getattr(settings, "server_status_channel_id", None),
            "loot_events": getattr(settings, "loot_events_channel_id", None),
            "changelog": getattr(settings, "changefeed_channel_id", None),
        }

        for name, channel_id in channel_map.items():
            if not channel_id:
                continue
            try:
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    continue
                webhooks = await channel.webhooks()
                webhook = discord.utils.get(webhooks, name=f"EZSTREET {name.replace('_', ' ').title()}")

                if not webhook:
                    webhook = await channel.create_webhook(
                        name=f"EZSTREET {name.replace('_', ' ').title()}", reason="Autonomous live updates system"
                    )
                self.webhooks[name] = webhook
            except Exception as e:
                log.error(f"Failed to setup webhook for {name}: {e}")

    async def _server_status_loop(self):
        """Standard async loop for supervisor management."""
        while True:
            try:
                self.bot.supervisor.heartbeat("server_status_update")
                await self.update_server_status()
            except Exception as e:
                log.error(f"[LIVE_UPDATES] Status loop error: {e}")
            await asyncio.sleep(60)

    async def update_server_status(self):
        """Update server status embed with coalescing and error handling."""
        if "server_status" not in self.webhooks:
            return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:19101/server/status", timeout=5) as resp:
                    if resp.status != 200:
                        return
                    data = await resp.json()

            status = data.get("status", "unknown")
            query = data.get("data", {}).get("query", {})
            player_count = query.get("player_current", 0)
            max_players = query.get("player_max", 60)
            server_map = query.get("map", "unknown")

            embed = discord.Embed(
                title="Server Status: EZStreet (Xbox)",
                color=discord.Color.green() if status == "started" else discord.Color.red(),
                timestamp=datetime.utcnow(),
            )
            embed.add_field(name="State", value=status.upper(), inline=True)
            embed.add_field(name="Players", value=f"**{player_count}/{max_players}**", inline=True)
            embed.add_field(name="Map", value=server_map, inline=True)
            embed.set_footer(text="Powered by Antigravity Modules • High-Fidelity Liveness ✅")

            webhook = self.webhooks["server_status"]
            if self.server_status_message_id:
                try:
                    message = await webhook.fetch_message(self.server_status_message_id)
                    await message.edit(embed=embed)
                except discord.NotFound:
                    msg = await webhook.send(embed=embed, username="EZStreet", wait=True)
                    self.server_status_message_id = msg.id
            else:
                msg = await webhook.send(embed=embed, username="EZStreet", wait=True)
                self.server_status_message_id = msg.id
        except Exception as e:
            log.error(f"[LIVE_UPDATES] Update logic error: {e}")

    async def robust_send(self, webhook_key: str, embed: discord.Embed, username: str = "EZStreet"):
        """
        Robust webhook sender with:
        1. Circuit Breaker protection
        2. Dry-Run mode
        3. 429 Rate Limit backoff
        4. Failure Simulation
        """
        import os

        from .utils.resilience import CircuitBreaker, CircuitState

        # Initialize CB if needed (lazy init)
        if not hasattr(self, "circuit"):
            self.circuit = CircuitBreaker("discord_webhook", failure_threshold=5, recovery_timeout=60)

        # 1. Check Dry Run / Circuit State
        if os.getenv("DISCORD_DRY_RUN", "false").lower() == "true":
            log.info(f"[DRY_RUN] Would send to {webhook_key}: {embed.title} | {embed.description}")
            return

        if self.circuit.state == CircuitState.OPEN:
            log.warning(f"[CIRCUIT_OPEN] Dropping message to {webhook_key}")
            return

        # 2. Failure Simulation
        sim_mode = os.getenv("DISCORD_FAIL_SIM")
        if sim_mode == "429":
            # Simulate 429: Log and backoff (mock behavior)
            log.warning("[SIMULATION] 429 Rate Limit hit! Backing off...")
            await asyncio.sleep(2)
            # We don't block forever in sim, just prove we handled it without crashing
            return
        elif sim_mode == "500":
            # Simulate server error to trip circuit
            await self.circuit.call(self._simulate_failure)
            return

        # 3. Actual Send with Retry/Circuit
        webhook = self.webhooks.get(webhook_key)
        if not webhook:
            return

        try:
            # We wrap the actual sending in the circuit breaker
            await self.circuit.call(self._do_send, webhook, embed, username)
        except Exception as e:
            log.error(f"[ROBUST_SEND] Failed to send to {webhook_key}: {e}")

    async def _simulate_failure(self):
        raise Exception("Simulated 500 Error for Circuit Breaker Test")

    async def _do_send(self, webhook, embed, username):
        # Retry loop for 429s handling
        retries = 3
        for _i in range(retries):
            try:
                await webhook.send(embed=embed, username=username, wait=True)
                return
            except discord.HTTPException as e:
                if e.status == 429:
                    retry_after = e.retry_after if hasattr(e, "retry_after") else 5
                    log.warning(f"Rate limited. Sleeping {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                raise e

    async def push_killfeed(self, event: dict):
        if "killfeed" not in self.webhooks:
            return
        try:
            ts = datetime.fromisoformat(event.get("timestamp")) if event.get("timestamp") else datetime.utcnow()
            embed = discord.Embed(title="💀 Combat Event", color=discord.Color.red(), timestamp=ts)
            killer = event.get("killer")
            victim = event.get("victim")
            embed.description = f"**{killer}** eliminated **{victim}**" if killer else f"**{victim}** died"
            if event.get("weapon"):
                embed.add_field(name="🔫 Weapon", value=event["weapon"], inline=True)
            if event.get("distance"):
                embed.add_field(name="📏 Distance", value=f"{event['distance']}m", inline=True)
            if event.get("location"):
                embed.add_field(name="📍 Location", value=event["location"], inline=False)

            await self.robust_send("killfeed", embed, "Killfeed")
        except Exception as e:
            log.error(f"[LIVE_UPDATES] Killfeed error: {e}")

    async def push_admin_action(self, action: dict):
        if "admin_log" not in self.webhooks:
            return
        try:
            embed = discord.Embed(
                title=f"🛡️ Admin Action: {action.get('type')}", color=discord.Color.gold(), timestamp=datetime.utcnow()
            )
            embed.add_field(name="Admin", value=action.get("admin", "System"), inline=True)
            if action.get("target"):
                embed.add_field(name="Target", value=action["target"], inline=True)
            embed.add_field(name="Reason", value=action.get("reason", "N/A"), inline=False)
            await self.robust_send("admin_log", embed, "Admin Logger")
        except Exception as e:
            log.error(f"[LIVE_UPDATES] Admin log error: {e}")

    async def push_loot_event(self, event: dict):
        if "loot_events" not in self.webhooks:
            return
        try:
            embed = discord.Embed(
                title=f"🚁 {event.get('type')}", color=discord.Color.blue(), timestamp=datetime.utcnow()
            )
            if event.get("location"):
                embed.add_field(name="📍 Location", value=event["location"], inline=True)
            embed.add_field(name="🎖️ Loot Tier", value=event.get("tier", "Military"), inline=True)
            if event.get("coords"):
                embed.add_field(name="Coordinates", value=f"`{event['coords']}`", inline=False)
            await self.robust_send("loot_events", embed, "Loot Scanner")
        except Exception as e:
            log.error(f"[LIVE_UPDATES] Loot event error: {e}")


async def setup(bot: OpsBot):
    live_updates = LiveUpdateSystem(bot)
    bot.live_updates = live_updates
    asyncio.create_task(live_updates.setup())
    log.info("✅ Live updates system initialized")
