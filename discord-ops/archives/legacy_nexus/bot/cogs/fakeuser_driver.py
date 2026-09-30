import asyncio
import random
import logging
import discord
from discord.ext import commands, tasks
from pathlib import Path
import json
from datetime import datetime

log = logging.getLogger("fakeuser")

class FakeUserDriver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = False
        self.session_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.log_dir = Path(f"logs/selfplay/{self.session_id}")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.commands_log = self.log_dir / "commands.log"
        self.responses_log = self.log_dir / "responses.log"
        self.metrics_file = self.log_dir / "metrics.json"
        
        # Metrics
        self.stats = {
            "commands_sent": 0,
            "errors": 0,
            "responses_captured": 0
        }

    async def cog_load(self):
        # Only start if enabled via env (or forced for now since we are implementing the harness)
        import os
        if os.getenv("ENABLE_SELFPLAY", "false").lower() == "true":
            log.info(f"DSIH: Starting Self-Play Loop (Session {self.session_id})")
            self.active = True
            self.loop.start()
        else:
            log.info("DSIH: Self-Play Cog loaded but dormant (ENABLE_SELFPLAY!=true)")

    async def cog_unload(self):
        self.loop.cancel()
        if self.active:
            self._write_metrics()

    def _log_command(self, user: str, cmd: str):
        with open(self.commands_log, "a") as f:
            f.write(f"[{datetime.utcnow().isoformat()}] {user}: {cmd}\n")
        self.stats["commands_sent"] += 1

    def _write_metrics(self):
        with open(self.metrics_file, "w") as f:
            json.dump(self.stats, f, indent=2)

    @tasks.loop(seconds=5.0) # Faster than 15s for the stress test
    async def loop(self):
        try:
            guilds = self.bot.guilds
            if not guilds: return
            guild = guilds[0] # Target first available guild

            # Ensure channel exists
            channel = discord.utils.get(guild.text_channels, name="🧪-sandbox")
            if not channel:
                channel = await guild.create_text_channel("🧪-sandbox")

            # Generate Traffic
            user_id = f"user_fake_{random.randint(1000, 9999)}"
            
            # Weighted choice of commands
            actions = [
               # ("!casino spin", 40),
               # ("!bank deposit 100", 20),
                ("!dayz_status", 20), # Use actual commands derived from bot.py
                ("!dayz_players", 20),
                ("!stat_tick", 5)
            ]
            
            # Flatten weighted list
            choices = []
            for cmd, weight in actions:
                choices.extend([cmd] * weight)
            
            cmd = random.choice(choices)
            
            msg_content = f"§SYNTH {user_id} {cmd}"
            
            # Send
            await channel.send(msg_content)
            self._log_command(user_id, cmd)
            
            # Log response
            await asyncio.sleep(1.0)
            async for m in channel.history(limit=3):
                if m.author == self.bot.user and m.embeds:
                    with open(self.responses_log, "a") as f:
                        f.write(f"RESP> {m.jump_url} :: {len(m.embeds)} embeds\n")
                    self.stats["responses_captured"] += 1

            self._write_metrics()

        except Exception as e:
            self.stats["errors"] += 1
            log.error(f"DSIH Loop Error: {e}")

    @loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(FakeUserDriver(bot))
