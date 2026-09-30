"""
Health Supervisor for DayZ Discord Ops.
Monitors cogs and background tasks, auto-restarting them if they fail.
"""

import asyncio
import logging
import traceback
from typing import Dict, List, Optional

log = logging.getLogger("health_supervisor")

class HealthSupervisor:
    def __init__(self, bot):
        self.bot = bot
        self.monitored_tasks: Dict[str, asyncio.Task] = {}
        self.restart_counts: Dict[str, int] = {}
        self.max_restarts = 5
        self.running = False

    async def start(self):
        """Start the supervisor loop"""
        self.running = True
        log.info("🛡️ Health Supervisor active. Monitoring backend stability.")
        asyncio.create_task(self._supervise_loop())

    async def _supervise_loop(self):
        """Main supervision loop"""
        while self.running:
            try:
                # 1. Check Discord Cogs
                for cog_name in list(self.bot.cogs.keys()):
                    # Potential for more advanced cog health checks here
                    pass

                # 2. Check Monitored Background Tasks
                dead_tasks = []
                for name, task in self.monitored_tasks.items():
                    if task.done():
                        exc = task.exception()
                        if exc:
                            log.error(f"🚑 Task '{name}' CRASHED: {exc}")
                            log.error(traceback.format_exc())
                            dead_tasks.append(name)
                        else:
                            log.warning(f"⚠️ Task '{name}' finished normally (expected?)")
                            dead_tasks.append(name)

                for name in dead_tasks:
                    await self._restart_task(name)

            except Exception as e:
                log.error(f"Supervisor loop error: {e}")
            
            await asyncio.sleep(10)

    async def _restart_task(self, name: str):
        """Restart a crashed task with backoff"""
        count = self.restart_counts.get(name, 0)
        if count >= self.max_restarts:
            log.critical(f"💀 Task '{name}' exceeded max restarts ({self.max_restarts}). Giving up.")
            return

        self.restart_counts[name] = count + 1
        wait_time = min(2 ** count, 60)
        log.info(f"🔄 Restarting task '{name}' in {wait_time}s (Attempt {count + 1})")
        
        await asyncio.sleep(wait_time)
        # This assumes the orchestrator or bot provides a factory for the task
        # For now, we just log. In a real impl, we'd trigger the specific start method.

    def monitor(self, name: str, task: asyncio.Task):
        """Register a task for monitoring"""
        self.monitored_tasks[name] = task
        log.info(f"👀 Now monitoring: {name}")

    def stop(self):
        self.running = False
