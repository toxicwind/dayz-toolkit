"""
Nitrado utilities and helper functions
"""
from datetime import datetime, timedelta
from typing import Any


def format_playtime(minutes: int) -> str:
    """Format playtime in minutes to human-readable string"""
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    mins = minutes % 60
    if hours < 24:
        return f"{hours}h {mins}m"
    days = hours // 24
    hours = hours % 24
    return f"{days}d {hours}h"


def calculate_uptime_percentage(crash_count: int, total_checks: int) -> float:
    """Calculate server uptime percentage"""
    if total_checks == 0:
        return 100.0
    return ((total_checks - crash_count) / total_checks) * 100


def is_resource_critical(cpu: float, ram: float) -> bool:
    """Check if resource usage is critical"""
    return cpu > 90 or ram > 95


def predict_crash_likelihood(cpu_trend: list[float], ram_trend: list[float]) -> float:
    """Simple crash prediction based on resource trends"""
    if not cpu_trend or not ram_trend:
        return 0.0
    
    # Check if trending upward
    cpu_increasing = all(cpu_trend[i] <= cpu_trend[i+1] for i in range(len(cpu_trend)-1))
    ram_increasing = all(ram_trend[i] <= ram_trend[i+1] for i in range(len(ram_trend)-1))
    
    # Check current levels
    cpu_high = cpu_trend[-1] > 80
    ram_high = ram_trend[-1] > 85
    
    if cpu_increasing and cpu_high and ram_increasing and ram_high:
        return 0.8
    elif (cpu_increasing and cpu_high) or (ram_increasing and ram_high):
        return 0.5
    elif cpu_high or ram_high:
        return 0.3
    
    return 0.1


def find_optimal_restart_window(player_history: list[dict]) -> datetime:
    """Find optimal time for server restart based on player activity"""
    # Find hour with lowest average player count
    hour_counts = {}
    for entry in player_history:
        hour = datetime.fromisoformat(entry['timestamp']).hour
        if hour not in hour_counts:
            hour_counts[hour] = []
        hour_counts[hour].append(entry['player_count'])
    
    # Calculate averages
    hour_averages = {h: sum(counts)/len(counts) for h, counts in hour_counts.items()}
    
    # Find lowest
    if not hour_averages:
        return datetime.now() + timedelta(hours=4)  # Default to 4 hours from now
    
    optimal_hour = min(hour_averages, key=hour_averages.get)
    
    # Schedule for next occurrence of that hour
    now = datetime.now()
    target = now.replace(hour=optimal_hour, minute=0, second=0, microsecond=0)
    if target < now:
        target += timedelta(days=1)
    
    return target


def format_alert_message(level: str, message: str) -> dict[str, Any]:
    """Format alert for Discord/frontend"""
    icons = {
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "CRITICAL": "🔴",
        "ERROR": "❌"
    }
    
    colors = {
        "INFO": 0x3498db,
        "WARNING": 0xf39c12,
        "CRITICAL": 0xe74c3c,
        "ERROR": 0xe74c3c
    }
    
    return {
        "icon": icons.get(level, "⚪"),
        "color": colors.get(level, 0x95a5a6),
        "level": level,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
