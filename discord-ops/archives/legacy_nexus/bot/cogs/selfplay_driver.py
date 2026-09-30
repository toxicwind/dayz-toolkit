import asyncio
import logging
import random
import discord
from discord import app_commands
from discord.ext import commands, tasks
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any

log = logging.getLogger("selfplay")

# Synthetic User Context
class SyntheticUser(discord.Object):
    def __init__(self, user_id: str, name: str, guild):
        super().__init__(id=int(user_id) if user_id.isdigit() else random.randint(10000, 99999))
        self.name = name
        self.display_name = name
        self.discriminator = "0000"
        self.bot = False
        self.guild = guild
        self.roles = []
        self.mention = f"<@{self.id}>"
        self._avatar = None

    @property
    def avatar(self):
        return self._avatar
    
    def __str__(self):
        return f"{self.name}#{self.discriminator}"

class SelfPlayDriver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = False
        self.scenario = None
        self.session_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.log_dir = Path(f"logs/burnin/{self.session_id}")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.events_log = self.log_dir / "selfplay_events.jsonl"
        self.scoreboard_channel_id = None
        self.stats = {
            "commands_sent": 0,
            "success": 0,
            "fail": 0,
            "scenarios_completed": []
        }
        self.target_channels = []
        
    @app_commands.command(name="selftest", description="Run a full end-to-end self-test simulation")
    async def selftest(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
            
        await interaction.response.send_message("🚀 Starting Protocol OMEGA Selftest...", ephemeral=True)
        await self.execute_instruction({"mode": "full_demo", "count": 3})
        await interaction.followup.send("✅ Selftest sequence initiated. Watch the channels.", ephemeral=True)

    async def cog_load(self):
        import os
        if os.getenv("ENABLE_SELFPLAY", "false").lower() == "true":
            log.info(f"SELFPLAY: Driver active (Session {self.session_id})")
            self.active = True
            await self.ensure_channels()
            self.loop.start()
        else:
             log.info("SELFPLAY: Driver loaded but inactive (ENABLE_SELFPLAY!=true)")

    async def cog_unload(self):
        self.loop.cancel()
    
    async def ensure_channels(self):
        settings = getattr(self.bot, 'settings', None)
        if not settings:
            return
        
        guild = self.bot.get_guild(settings.discord.guild_id)
        if not guild:
            return
        
        self.target_channels = []

        # 1. 🧪-selfplay (Default Sandbox)
        category = discord.utils.get(guild.categories, name='🧪 Ops')
        if not category:
            category = await guild.create_category('🧪 Ops')
            
        channel = discord.utils.get(guild.text_channels, name="🧪-selfplay")
        if not channel:
            channel = await guild.create_text_channel("🧪-selfplay", category=category)
        self.target_channels.append(channel)
        
        # 2. Emergent Discovery & Specific Targeting
        # User requested specific ID: 1452535146044461227
        specific_ids = [1452535146044461227, 1453978341076893868] 
        for cid in specific_ids:
            c = guild.get_channel(cid)
            if c:
                self.target_channels.append(c)
                log.info(f"SELFPLAY: Targeted specific channel {cid}")
            else:
                 # Try to fetch if not in cache (rare but possible)
                try:
                    c = await self.bot.fetch_channel(cid)
                    if c and c.guild.id == guild.id:
                        self.target_channels.append(c)
                        log.info(f"SELFPLAY: Fetched specific channel {cid}")
                except Exception:
                    log.warning(f"SELFPLAY: Could not find target channel {cid}")

        # Deploy feed for scoreboard
        feed_name = f"✨-{settings.org_id}-deploy-feed"
        self.feed_channel = discord.utils.get(guild.text_channels, name=feed_name)

    def _log_event(self, event: Dict[str, Any]):
        with open(self.events_log, "a") as f:
            f.write(json.dumps(event) + "\n")

    @tasks.loop(seconds=1.0)
    async def loop(self):
        # logging.info("SELFPLAY: Heartbeat") # Debug
        if not self.active or not self.target_channels:
            return
        
        # ... logic ...
        trigger_path = Path("state/selfplay_trigger.json")
        if trigger_path.exists():
            try:
                with open(trigger_path, "r") as f:
                    cmd_data = json.load(f)
                trigger_path.unlink() # Consume
                
                # Execute the instruction
                await self.execute_instruction(cmd_data)
            except Exception as e:
                log.error(f"Failed to process selfplay trigger: {e}")

    async def execute_instruction(self, instruction):
        if not self.target_channels:
            await self.ensure_channels()
            
        mode = instruction.get("mode")
        count = instruction.get("count", 1)
        
        log.info(f"SELFPLAY: Executing instruction {mode} x{count}")
        
        if mode == "casino_burst":
            await self.run_burst(["!casino spin", "!casino balance"], count, 10, "casino_user")
        elif mode == "banker_burst":
            await self.run_burst(["!bank deposit 10", "!bank withdraw 5", "!bank balance"], count, 5, "banker_user")
        elif mode == "status_storm":
            await self.run_burst(["!dayz_status", "!dayz_players"], count, 3, "status_user")
        elif mode == "emergent":
            await self.run_emergent_test()
        elif mode == "combat_simulation":
            await self.run_combat_simulation(count)
        elif mode == "full_demo":
            await self.run_full_live_demo()

    async def run_full_live_demo(self):
        log.info("SELFPLAY: Starting FULL LIVE DEMO with Emergent Discovery...")
        
        # 1. Discover Channels via Audit
        audit_cog = self.bot.get_cog("ChannelAudit")
        audit_map = {}
        if audit_cog:
            results = await audit_cog.run_audit()
            for res in results:
                if res.matched_feature:
                    audit_map[res.matched_feature] = res.channel_id
        
        guild = self.bot.get_guild(self.bot.settings.discord_guild_id)
        if not guild: return

        # 2. Status Board Sync
        status_cid = audit_map.get("status_board")
        if status_cid:
            chan = guild.get_channel(status_cid)
            if chan:
                log.info(f"SELFPLAY: Simulating status update in {chan.name}...")
                status_cog = self.bot.get_cog("StatusBoard")
                if status_cog:
                    await status_cog.update_status()
                await chan.send("`[SYNTH]` System Health Check: **GREEN** 🟢")

        # 3. ChangeFeed / Deployment
        feed_cid = audit_map.get("changefeed")
        if feed_cid:
            chan = guild.get_channel(feed_cid)
            if chan:
                await chan.send("🚀 **DEPLOYMENT COMPLETE**: Version `2025.omega.7` hot-swapped successfully.")
                await asyncio.sleep(2)

        # 4. Combat / Killfeed
        kill_cid = audit_map.get("killfeed")
        if kill_cid:
            chan = guild.get_channel(kill_cid)
            if chan:
                log.info(f"SELFPLAY: Starting combat simulation in {chan.name}...")
                await self.run_combat_simulation(3)

        # 5. Interaction Loop (Synthetic Commands)
        target = self.target_channels[0] if self.target_channels else None
        if target:
            await target.send("§SYNTH ezstreet_admin !dayz_status")
            await asyncio.sleep(3)
            await target.send("§SYNTH auditor_699 !trader list")
            await asyncio.sleep(3)
            await target.send("§SYNTH ezstreet_admin !dayz_players")
            await asyncio.sleep(3)
            await target.send("§SYNTH ezstreet_admin !stat_tick")

        log.info("SELFPLAY: FULL LIVE DEMO sequence completed.")

    async def run_status_simulation(self):
        status_cog = self.bot.get_cog("StatusBoard")
        if not status_cog:
            log.warning("SELFPLAY: StatusBoard cog not found.")
            return
            
        log.info("SELFPLAY: Simulating status update...")
        # Mock the probe_nitrado method temporarily
        original_probe = status_cog.probe_nitrado
        
        async def mock_probe():
            return {
                "status": "started",
                "query": {
                    "server_name": "〖LIVE DEMO〗 EZSTREET ALPHA",
                    "player_current": random.randint(45, 60),
                    "player_max": 60,
                    "version": "1.25.MOCK"
                }
            }
        
        status_cog.probe_nitrado = mock_probe
        await status_cog.update_status()
        status_cog.probe_nitrado = original_probe
        log.info("SELFPLAY: Status update simulated.")

    async def run_deploy_simulation(self):
        cf_cog = self.bot.get_cog("ChangeFeed")
        if not cf_cog:
            log.warning("SELFPLAY: ChangeFeed cog not found.")
            return
            
        log.info("SELFPLAY: Simulating deployment notification...")
        mock_commit = {
            "sha": "demo_sha_" + str(random.randint(1000, 9999)),
            "author": "ToxicWind",
            "subject": "Restored premium aesthetics and POI resolution system 〖PROD〗",
            "files": ["bot/killfeed.py", "config/services/ezstreet.yaml", "data/archives/pois.xml"],
            "diffstat": "3 files changed, 1573 insertions(+), 12 deletions(-)"
        }
        await cf_cog.post_card(mock_commit)
        log.info("SELFPLAY: Deployment notification simulated.")

    async def run_combat_simulation(self, count):
        from bot.log_streamer import get_streamer, LogEvent
        streamer = get_streamer()
        
        # Coordinates map to POIs in cfgeventspawns.xml
        # 4650, 8300 is near a Secret Military Crate (StaticContainerLocked)
        mock_lines = [
            '2025-12-26 05:00:00 | Player "StaleBread" (DEAD) (id=ABC pos=<4650.5, 150.0, 8300.2>) killed by Player "ToxicWind" (id=DEF pos=<4800.0, 160.0, 8400.0>) with M4A1 from 185.5 meters',
            '2025-12-26 05:01:00 | Player "Newbie" (DEAD) (id=GHI pos=<12000.0, 20.0, 3000.0>) died from falling',
            '2025-12-26 05:02:00 | Player "Survivor" (DEAD) (id=JKL pos=<6000.0, 10.0, 6000.0>) killed by explosion (Grenade_RGD5)',
            '2025-12-26 05:03:00 | Player "PoorSoul" (DEAD) (id=MNO pos=<2000.0, 5.0, 12000.0>) killed by ZmbM_PatrolNormal_Summer',
            '2025-12-26 05:04:00 | Player "Looter" (DEAD) (id=PQR pos=<11000.0, 15.0, 11000.0>) committed suicide',
            '2025-12-26 05:05:00 | Player "Hunter" (DEAD) (id=STU pos=<8000.0, 40.0, 2000.0>) killed by Animal_UrsusArctos'
        ]
        
        log.info(f"SELFPLAY: Starting combat simulation ({count} events)...")
        for i in range(count):
            line = mock_lines[i % len(mock_lines)]
            # Add some randomness to victim name for variety
            if "StaleBread" in line:
                line = line.replace("StaleBread", f"Victim_{random.randint(100, 999)}")
                
            event = LogEvent(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                source="rcon", 
                level="combat",
                message=line,
                raw=line
            )
            # Notify internal listeners directly
            await streamer._notify_listeners(event)
            log.info(f"SELFPLAY: Emitted mock combat event {i+1}/{count}")
            await asyncio.sleep(3.0) # Pause so user can see them one by one

    async def run_emergent_test(self):
        """
        Emergent test: Use ChannelAudit to identify channel types, 
        then run appropriate synthetic commands on each.
        """
        log.info("SELFPLAY: Starting EMERGENT channel test via ChannelAudit...")
        
        settings = getattr(self.bot, 'settings', None)
        if not settings: return
        guild = self.bot.get_guild(settings.discord.guild_id)
        if not guild: return

        # Get Audit Results
        audit_cog = self.bot.get_cog("ChannelAudit")
        if not audit_cog:
            log.error("SELFPLAY: ChannelAudit cog not loaded! Cannot run emergent test.")
            return
            
        scan_data = audit_cog.scan_guild(guild)
        results = scan_data['results'] # List of ChannelAuditResult

        # Feature -> Commands Map
        FEATURE_COMMANDS = {
            "casino": ["!casino spin", "!casino balance", "!casino slots"],
            "bank": ["!bank balance", "!bank deposit 10", "!bank withdraw 5"],
            "trader": ["!trader list", "!shop"],
            "tickets": ["!ticket create test_ticket", "!ticket help"],
            "status_board": ["!dayz_status", "!dayz_players"],
            "leaderboard": ["!leaderboard", "!top"],
            "general": ["!help", "!ping"],
            "bot": ["!help", "!uptime"]
        }

        actions_taken = 0
        
        for res in results:
            if not res.matched_feature:
                continue
                
            tasks = FEATURE_COMMANDS.get(res.matched_feature)
            if not tasks:
                continue

            channel = guild.get_channel(res.channel_id)
            if not channel: continue
            
            log.info(f"SELFPLAY: Targeted #{channel.name} ({res.matched_feature})")
            
            # Execute random command from the feature set
            cmd = random.choice(tasks)
            user_id = f"auditor_{random.randint(100, 999)}"
            content = f"§SYNTH {user_id} {cmd}"
            
            try:
                await channel.send(content)
                self._log_event({
                    "type": "emergent_test",
                    "channel": channel.name,
                    "feature": res.matched_feature,
                    "command": cmd,
                    "status": "sent"
                })
                actions_taken += 1
                await asyncio.sleep(0.5) 
            except Exception as e:
                log.error(f"SELFPLAY: Failed to act in #{channel.name}: {e}")

        log.info(f"SELFPLAY: Emergent test complete. Actions taken: {actions_taken}")

    async def run_burst(self, commands_list, count, user_pool_size, user_prefix):
        if not self.target_channels:
            log.warning("SELFPLAY: No channels to burst into.")
            return

        for i in range(count):
            start_ts = datetime.utcnow().timestamp()
            user_id = f"{user_prefix}_{random.randint(1, user_pool_size)}"
            cmd = random.choice(commands_list)
            
            # Rotate channels for "emergent" distribution
            target_channel = random.choice(self.target_channels)
            
            # Tag message with §SYNTH
            content = f"§SYNTH {user_id} {cmd}"
            try:
                await target_channel.send(content)
                self._log_event({
                    "type": "command",
                    "command": cmd,
                    "actor": user_id,
                    "timestamp": start_ts,
                    "channel": target_channel.id,
                    "status": "sent"
                })
            except Exception as e:
                 log.error(f"SELFPLAY: Failed to send to {target_channel.name}: {e}")
            
            await asyncio.sleep(0.1) # slight spacing

    @loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(SelfPlayDriver(bot))
