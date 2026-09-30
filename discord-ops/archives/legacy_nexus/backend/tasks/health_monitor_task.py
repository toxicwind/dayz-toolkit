"""
Automated health monitoring task for Discord bot

Runs in background and sends alerts to Discord channels.
"""
import asyncio
import logging
from discord.ext import tasks

from backend.health_monitor import get_monitor

log = logging.getLogger(__name__)


class HealthMonitorTask:
    """Background task for health monitoring"""
    
    def __init__(self, bot):
        self.bot = bot
        self.monitor = get_monitor()
        self.alert_channel_id = None  # Set from config
        
        # Add Discord alert callback
        self.monitor.add_alert_callback(self.send_discord_alert)
    
    async def send_discord_alert(self, level: str, message: str):
        """Send alert to Discord channel"""
        if not self.alert_channel_id:
            return
        
        channel = self.bot.get_channel(self.alert_channel_id)
        if not channel:
            return
        
        # Color based on level
        color_map = {
            "INFO": "🟢",
            "WARNING": "🟡",
            "CRITICAL": "🔴",
            "ERROR": "🔴"
        }
        
        icon = color_map.get(level, "⚪")
        await channel.send(f"{icon} **[{level}]** {message}")
    
    @tasks.loop(seconds=30)
    async def monitor_loop(self):
        """Main monitoring loop"""
        try:
            # Check for crash
            if await self.monitor.detect_crash():
                # Auto-restart handled by monitor
                pass
            
            # Perform health check
            metrics = await self.monitor.check_health()
            
            # Alerts are sent via callback
            
        except Exception as e:
            log.error(f"Health monitor task error: {e}")
    
    @monitor_loop.before_loop
    async def before_monitor_loop(self):
        await self.bot.wait_until_ready()
    
    def start(self):
        """Start monitoring task"""
        self.monitor_loop.start()
    
    def stop(self):
        """Stop monitoring task"""
        self.monitor_loop.cancel()
