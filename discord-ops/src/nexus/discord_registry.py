import json
import logging
import os
import asyncio
from pathlib import Path
from typing import Dict, Optional, Any, List

import discord

log = logging.getLogger("mildlyawesome.registry")

class DiscordRegistry:
    """
    Chronos Channel Registry Engine v2.

    Responsibility:
    - Load declarative spec (channel_spec.json)
    - Load/Save authoritative state (channel_state.json)
    - Resolve semantic keys to actual Discord Channel IDs
    - Orchestrate reconstitution (Sync)
    - Enforce Private Category Invariant
    """

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        # Paths
        self.spec_path = repo_root / "src/mildlyawesome/discord/channel_spec.json"
        self.state_path = repo_root / "src/mildlyawesome/discord/discord_channel_map.json"
        
        self.spec: Dict[str, Any] = {}
        self.state: Dict[str, Any] = {}
        self.target_category_id: int = 0
        
        self._reload()

    def _reload(self):
        """Load spec and state from disk."""
        if self.spec_path.exists():
            with open(self.spec_path, "r") as f:
                self.spec = json.load(f)
                self.target_category_id = self.spec.get("target_category_id", 0)
        else:
            log.warning(f"Registry spec not found at {self.spec_path}")

        if self.state_path.exists():
            with open(self.state_path, "r") as f:
                self.state = json.load(f)
        
        # Ensure schema structure exists
        if "assignments" not in self.state:
            self.state["assignments"] = {}
        if "metadata" not in self.state:
            self.state["metadata"] = {"last_migration": None}

    def save_state(self):
        """Persist state to discord_channel_map.json (Atomically)."""
        temp = self.state_path.with_suffix(".tmp")
        with open(temp, "w") as f:
            json.dump(self.state, f, indent=2)
        temp.rename(self.state_path)

    def resolve(self, key: str) -> Optional[int]:
        """
        Resolve a semantic key (e.g., 'ops.status') to its NEW Discord Channel ID.
        If no new ID exists, returns None.
        """
        sid = self.state.get("assignments", {}).get(key)
        return int(sid) if sid else None

    async def sync(self, guild: discord.Guild, dry_run: bool = False) -> Dict[str, str]:
        """
        Reconstitute channels based on spec.

        1. Validate Target Category (Private Only)
        2. Create Missing Channels (New) under Private Category
        3. Document Migration
        4. Lock Legacy Channels if encountered
        """
        if not self.target_category_id:
            return {"error": "Target category ID not defined in spec"}

        category = guild.get_channel(self.target_category_id)
        if not category or not isinstance(category, discord.CategoryChannel):
            log.error(f"Target private category {self.target_category_id} not found or not a category")
            return {"error": f"Target category {self.target_category_id} missing"}

        log.info(f"Syncing to Private Category: {category.name} ({category.id})")
        
        # --- Permission Sync ---
        if self.spec.get("permissions", {}).get("sync_enabled"):
            await self._sync_category_permissions(category, dry_run)

        report = {}
        assignments = self.state.get("assignments", {})
        
        # In-memory update of assignments to return consistent state even in dry-run
        pending_assignments = assignments.copy()

        for key, chan_def in self.spec.get("channels", {}).items():
            current_id = pending_assignments.get(key)
            channel = guild.get_channel(int(current_id)) if current_id else None
            
            # --- Invariant Check: Must be in Private Category ---
            must_recreate = False
            if channel:
                if channel.category_id != self.target_category_id:
                    log.info(f"Channel {key} ({channel.id}) found outside private category.")
                    must_recreate = True
                else:
                    # Sync metadata if needed
                    meta_report = await self._sync_channel_metadata(channel, chan_def, dry_run)
                    if meta_report:
                        report[f"{key}.meta"] = meta_report

                    # Webhook Adoption
                    if "webhooks" in chan_def:
                        await self._sync_channel_webhooks(channel, chan_def["webhooks"], dry_run)
                    
                    # Retention Sync (Manual trigger usually, but check spec)
                    if "retention_days" in chan_def and not dry_run:
                         # We don't auto-purge on every sync to avoid rate limits,
                         # but we mark it as 'Retention Managed'
                         report[f"{key}.retention"] = f"{chan_def['retention_days']} days"

            if not channel or must_recreate:
                legacy_action = ""
                if must_recreate and channel:
                    # LOCK THE OLD CHANNEL
                    legacy_action = await self._lock_legacy_channel(channel, dry_run)
                    report[f"{key}.legacy_lock"] = legacy_action
                    channel = None # Clear ref so we create new

                # CREATE NEW
                if not dry_run:
                    try:
                        if chan_def.get("type") == "voice":
                            channel = await guild.create_voice_channel(
                                name=chan_def["name"],
                                category=category,
                                position=chan_def.get("position", 0)
                            )
                        else:
                            channel = await guild.create_text_channel(
                                name=chan_def["name"],
                                category=category,
                                topic=chan_def.get("topic", "Reconstituted by Chronos"),
                                position=chan_def.get("position", 0)
                            )
                        report[key] = f"CREATED NEW: {channel.id} in Private Category"
                        pending_assignments[key] = str(channel.id)
                    except Exception as e:
                        log.error(f"Failed to create {key}: {e}")
                        report[key] = f"ERROR: {e}"
                else:
                    report[key] = f"[Dry Run] Would create NEW {key} in Private Category"
                    if must_recreate:
                        report[key] += " (Replacing existing external channel)"

            else:
                 report[key] = f"OK: {channel.id} (In Position)"

            # Ensure we update state even if we just confirmed it exists
            if channel and not dry_run:
                 pending_assignments[key] = str(channel.id)

        if not dry_run:
            self.state["assignments"] = pending_assignments
            import datetime
            self.state["metadata"]["last_migration"] = datetime.datetime.utcnow().isoformat()
            self.save_state()

        return report

    async def _lock_legacy_channel(self, channel: discord.abc.GuildChannel, dry_run: bool) -> str:
        """Lock a channel (ReadOnly) and tag it as migrated."""
        if dry_run:
            return f"[Dry Run] Would LOCK {channel.name} ({channel.id})"
        
        try:
            # Overwrite permissions: Deny Send for Everyone
            await channel.set_permissions(channel.guild.default_role, send_messages=False, add_reactions=False)
            
            # Rename if text channel
            if isinstance(channel, discord.TextChannel):
                 new_name = f"🔒-{channel.name}"
                 # Discord limit 100 chars
                 new_name = new_name[:100]
                 await channel.edit(name=new_name, topic=f"MIGRATED: Content moved to Private Ops Category. {channel.topic or ''}"[:1024])
            
            return f"LOCKED {channel.id}"
        except Exception as e:
            return f"FAILED LOCK {channel.id}: {e}"

    async def _sync_category_permissions(self, category: discord.CategoryChannel, dry_run: bool):
        """Standardize permissions across the entire Ops category."""
        perm_spec = self.spec.get("permissions", {})
        if not perm_spec:
            return

        overwrites = category.overwrites
        changed = False

        # Lockdown @everyone
        everyone_overwrites = overwrites.get(category.guild.default_role, discord.PermissionOverwrite())
        if everyone_overwrites.view_channel is not False or everyone_overwrites.send_messages is not False:
            everyone_overwrites.view_channel = False
            everyone_overwrites.send_messages = False
            overwrites[category.guild.default_role] = everyone_overwrites
            changed = True
            log.info("Applying @everyone lockdown to category")

        # Bot Overrides (Self)
        bot_member = category.guild.me
        bot_overwrites = overwrites.get(bot_member, discord.PermissionOverwrite())
        bot_perms = perm_spec.get("bot_overrides", [])
        
        bot_changed = False
        for p in bot_perms:
            if hasattr(bot_overwrites, p):
                if getattr(bot_overwrites, p, None) is not True:
                    setattr(bot_overwrites, p, True)
                    bot_changed = True
            else:
                log.warning(f"Permission attribute '{p}' not supported by this discord.py version.")
        
        # Explicit bit for 2026 PIN_MESSAGES requirement - handled by the loop if in spec, 
        # but spec might use a different name or library might be too old.

        if bot_changed:
            overwrites[bot_member] = bot_overwrites
            changed = True
            log.info("Updating bot overrides in category")

        if changed and not dry_run:
            await category.edit(overwrites=overwrites)
            log.info(f"Synchronized permissions for category {category.name}")

    async def _sync_channel_metadata(self, channel: discord.abc.GuildChannel, spec: Dict[str, Any], dry_run: bool) -> List[str]:
        """Update channel name, topic, and position to match spec."""
        updates = []
        
        # Name check
        target_name = spec["name"]
        if channel.name != target_name:
            updates.append(f"NAME: {channel.name} -> {target_name}")
            if not dry_run:
                await channel.edit(name=target_name)

        # Topic check (text only)
        if isinstance(channel, discord.TextChannel):
            target_topic = spec.get("topic", "")
            if channel.topic != target_topic:
                 updates.append(f"TOPIC: {len(channel.topic or '')} -> {len(target_topic)} chars")
                 if not dry_run:
                     await channel.edit(topic=target_topic)

        # Position check
        target_pos = spec.get("position")
        if target_pos is not None and channel.position != target_pos:
            updates.append(f"POS: {channel.position} -> {target_pos}")
            if not dry_run:
                await channel.edit(position=target_pos)

        # Slowmode check (text only)
        if isinstance(channel, discord.TextChannel):
            target_slow = spec.get("slowmode", 0)
            if channel.slowmode_delay != target_slow:
                updates.append(f"SLOWMODE: {channel.slowmode_delay}s -> {target_slow}s")
                if not dry_run:
                    await channel.edit(slowmode_delay=target_slow)

        # Metrics Gauge check
        if spec.get("gauge"):
            await self._sync_channel_gauge(channel, dry_run)

        return updates

    async def _sync_channel_gauge(self, channel: discord.abc.GuildChannel, dry_run: bool):
        """Update a channel topic with pseudo-live metrics."""
        # Baseline topic from spec
        base_topic = "Live Metrics Gauge | Managed by Chronos"
        
        # Mock Metrics for Sync (In a real bot, this pulls from health_monitor)
        # We use it here to ensure the spec is applied during 'discord_migrate'
        metrics_str = "Health: ✅ | Status: started | Players: 0 | CPU: 12.0% | RAM: 4.5GB"
        new_topic = f"{base_topic}\n\n{metrics_str}\nUpdated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"

        if channel.topic != new_topic:
            log.info(f"Updating metrics gauge on {channel.name}")
            if not dry_run:
                await channel.edit(topic=new_topic)

    async def purge_stale_logs(self, guild: discord.Guild, dry_run: bool = True) -> Dict[str, int]:
        """Iterate all managed channels and purge messages older than retention_days."""
        results = {}
        for key, chan_def in self.spec.get("channels", {}).items():
            days = chan_def.get("retention_days")
            if not days:
                continue
            
            channel_id = self.resolve(key)
            if not channel_id:
                continue
                
            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                continue
                
            log.info(f"Purging logs for {key} older than {days} days...")
            if dry_run:
                results[key] = 0 # Cannot accurately count in dry run without full history scan
                continue
            
            # Use 14 days as hard cap (Discord API limit for bulk delete)
            actual_days = min(days, 14)
            before = datetime.datetime.utcnow() - datetime.timedelta(days=actual_days)
            
            try:
                deleted = await channel.purge(before=before, bulk=True)
                results[key] = len(deleted)
                log.info(f"Deleted {len(deleted)} messages from {key}")
            except Exception as e:
                log.error(f"Purge failed for {key}: {e}")
                results[key] = -1
                
        return results

    async def _sync_channel_webhooks(self, channel: discord.abc.GuildChannel, desired_names: List[str], dry_run: bool):
        """Ensure specific webhooks exist for the channel."""
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            existing_webhooks = await channel.webhooks()
            existing_names = [w.name for w in existing_webhooks]

            for name in desired_names:
                if name not in existing_names:
                    log.info(f"Creating missing webhook '{name}' for channel {channel.name}")
                    if not dry_run:
                        await channel.create_webhook(name=name, reason="Chronos Managed Webhook")
        except Exception as e:
            log.error(f"Failed to sync webhooks for {channel.name}: {e}")
