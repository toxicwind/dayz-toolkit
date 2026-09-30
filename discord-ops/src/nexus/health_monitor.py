"""
Automated Server Health Monitoring

Monitors server health via Nitrado API and provides:
- CPU/RAM usage alerts
- Crash detection and auto-restart
- Performance degradation warnings
- Resource usage trending

Integrates with Discord for alerts and status updates.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from .config import load_settings
from .nitrado_sdk_client import create_client_from_config

log = logging.getLogger("dayz-discord-ops.health-monitor")


class HealthMetrics:
    """Container for health check results"""
    def __init__(self):
        self.timestamp = datetime.now()
        self.status: str = "unknown"
        self.cpu_usage: float = 0.0
        self.ram_usage: float = 0.0
        self.player_count: int = 0
        self.is_healthy: bool = True
        self.alerts: list[str] = []
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "cpu_usage": self.cpu_usage,
            "ram_usage": self.ram_usage,
            "player_count": self.player_count,
            "is_healthy": self.is_healthy,
            "alerts": self.alerts
        }


class ServerHealthMonitor:
    """Monitors server health and triggers alerts/actions"""
    
    # Thresholds
    CPU_WARNING = 75.0
    CPU_CRITICAL = 90.0
    RAM_WARNING = 80.0
    RAM_CRITICAL = 95.0
    
    def __init__(self, service: str = "ezstreet"):
        self.service = service
        self.settings = load_settings(service=service)
        self.client = create_client_from_config(service=service)
        
        # State tracking
        self.last_status = "unknown"
        self.crash_count = 0
        self.last_metrics: HealthMetrics | None = None
        self.metrics_history: list[HealthMetrics] = []
        
        # Alert callbacks
        self.alert_callbacks: list = []
    
    def add_alert_callback(self, callback):
        """Add callback for alerts (e.g., Discord notification)"""
        self.alert_callbacks.append(callback)
    
    async def _trigger_alert(self, level: str, message: str):
        """Trigger alert to all registered callbacks"""
        log.warning(f"[{level}] {message}")
        for callback in self.alert_callbacks:
            try:
                await callback(level, message)
            except Exception as e:
                log.error(f"Alert callback failed: {e}")
    
    async def check_health(self) -> HealthMetrics:
        """Perform comprehensive health check"""
        metrics = HealthMetrics()
        
        try:
            # Get server status
            metrics.status = await self.client.get_status()
            
            # Get current players
            try:
                players = await self.client.get_players()
                metrics.player_count = len(players)
            except Exception as e:
                log.warning(f"Could not get players: {e}")
            
            # Get resource usage (last hour)
            try:
                stats = await self.client.get_resource_usage(hours=1)
                
                # Extract latest metrics (SDK returns time series)
                if isinstance(stats, dict):
                    # Parse CPU/RAM from stats structure
                    # Note: Actual structure depends on Nitrado API response
                    metrics.cpu_usage = self._extract_latest_metric(stats, 'cpu')
                    metrics.ram_usage = self._extract_latest_metric(stats, 'ram')
            except Exception as e:
                log.warning(f"Could not get resource usage: {e}")
            
            # Analyze health
            metrics.is_healthy = self._analyze_health(metrics)
            
            # Store in history
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > 100:  # Keep last 100
                self.metrics_history.pop(0)
            
            self.last_metrics = metrics
            
        except Exception as e:
            log.error(f"Health check failed: {e}")
            metrics.is_healthy = False
            metrics.alerts.append(f"Health check error: {e}")
        
        return metrics
    
    def _extract_latest_metric(self, stats: dict, metric: str) -> float:
        """Extract latest value from stats time series"""
        # This is a placeholder - actual implementation depends on API response structure
        # Nitrado API might return: {"cpu": [{"timestamp": ..., "value": 45.2}, ...]}
        try:
            if metric in stats and isinstance(stats[metric], list) and len(stats[metric]) > 0:
                return float(stats[metric][-1].get('value', 0))
            return 0.0
        except:
            return 0.0
    
    def _analyze_health(self, metrics: HealthMetrics) -> bool:
        """Analyze metrics and generate alerts"""
        is_healthy = True
        
        # Check server status
        if metrics.status == "stopped":
            metrics.alerts.append("🔴 Server is STOPPED")
            is_healthy = False
        elif metrics.status != "started":
            metrics.alerts.append(f"⚠️ Server status: {metrics.status}")
            is_healthy = False
        
        # Check CPU usage
        if metrics.cpu_usage >= self.CPU_CRITICAL:
            metrics.alerts.append(f"🔴 CRITICAL CPU: {metrics.cpu_usage:.1f}%")
            is_healthy = False
        elif metrics.cpu_usage >= self.CPU_WARNING:
            metrics.alerts.append(f"⚠️ High CPU: {metrics.cpu_usage:.1f}%")
        
        # Check RAM usage
        if metrics.ram_usage >= self.RAM_CRITICAL:
            metrics.alerts.append(f"🔴 CRITICAL RAM: {metrics.ram_usage:.1f}%")
            is_healthy = False
        elif metrics.ram_usage >= self.RAM_WARNING:
            metrics.alerts.append(f"⚠️ High RAM: {metrics.ram_usage:.1f}%")
        
        return is_healthy
    
    async def detect_crash(self) -> bool:
        """Detect if server has crashed"""
        try:
            status = await self.client.get_status()
            
            # Crash detected if status changed from started to stopped
            if self.last_status == "started" and status == "stopped":
                self.crash_count += 1
                log.error(f"CRASH DETECTED! Count: {self.crash_count}")
                await self._trigger_alert("CRITICAL", f"🔴 Server crash detected! (crash #{self.crash_count})")
                self.last_status = status
                return True
            
            self.last_status = status
            return False
            
        except Exception as e:
            log.error(f"Crash detection failed: {e}")
            return False
    
    async def auto_restart(self, reason: str = "Auto-recovery from crash"):
        """Attempt automatic server restart"""
        try:
            log.info(f"Attempting auto-restart: {reason}")
            await self._trigger_alert("WARNING", f"🔄 Attempting auto-restart: {reason}")
            
            # Try to start the server
            result = await self.client.restart_server(message=reason)
            
            if result.get("status") == "success":
                log.info("Auto-restart initiated successfully")
                await self._trigger_alert("INFO", "✅ Auto-restart initiated")
                
                # Wait for server to come back up
                await asyncio.sleep(60)
                
                # Verify restart
                status = await self.client.get_status()
                if status == "started":
                    await self._trigger_alert("INFO", "✅ Server restarted successfully!")
                    return True
                else:
                    await self._trigger_alert("WARNING", f"⚠️ Server status after restart: {status}")
                    return False
            else:
                log.error(f"Auto-restart failed: {result}")
                await self._trigger_alert("ERROR", f"❌ Auto-restart failed: {result.get('message')}")
                return False
                
        except Exception as e:
            log.error(f"Auto-restart error: {e}")
            await self._trigger_alert("ERROR", f"❌ Auto-restart error: {e}")
            return False
    
    async def monitor_loop(self, interval: int = 30):
        """Main monitoring loop"""
        log.info(f"Starting health monitor (interval: {interval}s)")
        
        while True:
            try:
                # Check for crash
                if await self.detect_crash():
                    # Auto-restart on crash
                    await self.auto_restart("Crash detected - auto-recovery")
                
                # Perform health check
                metrics = await self.check_health()
                
                # Trigger alerts for any issues
                for alert in metrics.alerts:
                    # Determine alert level
                    if "🔴" in alert or "CRITICAL" in alert:
                        await self._trigger_alert("CRITICAL", alert)
                    elif "⚠️" in alert:
                        await self._trigger_alert("WARNING", alert)
                    else:
                        await self._trigger_alert("INFO", alert)
                
                # Log summary
                log.info(
                    f"Health: {'✅' if metrics.is_healthy else '❌'} | "
                    f"Status: {metrics.status} | "
                    f"Players: {metrics.player_count} | "
                    f"CPU: {metrics.cpu_usage:.1f}% | "
                    f"RAM: {metrics.ram_usage:.1f}%"
                )
                
            except Exception as e:
                log.error(f"Monitor loop error: {e}")
            
            await asyncio.sleep(interval)
    
    def get_health_summary(self) -> dict[str, Any]:
        """Get current health summary"""
        if not self.last_metrics:
            return {"status": "no_data", "message": "No health data available yet"}
        
        return {
            "status": "healthy" if self.last_metrics.is_healthy else "unhealthy",
            "metrics": self.last_metrics.to_dict(),
            "crash_count": self.crash_count,
            "history_size": len(self.metrics_history)
        }


# Global monitor instance
_monitor: ServerHealthMonitor | None = None


def get_monitor(service: str = "ezstreet") -> ServerHealthMonitor:
    """Get or create global health monitor"""
    global _monitor
    if _monitor is None:
        _monitor = ServerHealthMonitor(service=service)
    return _monitor


async def start_monitoring(service: str = "ezstreet", interval: int = 30):
    """Start health monitoring in background"""
    monitor = get_monitor(service)
    await monitor.monitor_loop(interval=interval)
