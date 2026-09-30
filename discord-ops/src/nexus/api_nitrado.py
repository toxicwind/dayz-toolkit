"""
Backend API endpoints for Nitrado SDK integration

Provides REST API for frontend to access Nitrado functionality.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .nitrado_sdk_client import create_client_from_config
from .health_monitor import get_monitor

router = APIRouter(prefix="/api/nitrado", tags=["nitrado"])


# Health endpoints
@router.get("/health/summary")
async def get_health_summary():
    """Get current server health summary"""
    monitor = get_monitor()
    return monitor.get_health_summary()


# Backup endpoints
@router.get("/backups")
async def list_backups():
    """List available backups"""
    client = create_client_from_config()
    backups = await client.list_backups()
    return {"backups": backups}


@router.post("/backups/create")
async def create_backup(name: str = None):
    """Create new backup snapshot"""
    client = create_client_from_config()
    success = await client.create_settings_snapshot(name=name)
    return {"success": success}


@router.post("/backups/{backup_id}/restore")
async def restore_backup(backup_id: str):
    """Restore from backup"""
    client = create_client_from_config()
    success = await client.restore_backup("gameserver", backup_id)
    return {"success": success}


# Player management endpoints
@router.get("/players/sessions")
async def get_player_sessions():
    """Get current player sessions"""
    client = create_client_from_config()
    players = await client.get_players()
    
    # Transform to session format
    sessions = [
        {
            "player_id": p.get("id", "unknown"),
            "player_name": p.get("name", "Unknown"),
            "join_time": p.get("join_time", ""),
            "playtime_minutes": p.get("playtime", 0),
            "kills": 0,  # Would need to fetch from analytics
            "deaths": 0,
            "status": "online"
        }
        for p in players
    ]
    return {"sessions": sessions}


@router.get("/whitelist")
async def get_whitelist():
    """Get whitelisted players"""
    # This would need custom implementation
    return {"players": []}


class AddPlayerRequest(BaseModel):
    gamertag: str


@router.post("/whitelist/add")
async def add_to_whitelist(req: AddPlayerRequest):
    """Add player to whitelist"""
    client = create_client_from_config()
    success = await client.whitelist_player(req.gamertag)
    return {"success": success}


@router.get("/admins")
async def get_admins():
    """Get admin players"""
    client = create_client_from_config()
    admins = await client.get_admin_list()
    return {"players": admins}


@router.post("/admins/add")
async def add_admin(req: AddPlayerRequest):
    """Make player admin"""
    client = create_client_from_config()
    success = await client.make_admin(req.gamertag)
    return {"success": success}


# Resource monitoring endpoints
@router.get("/resources")
async def get_resource_usage(hours: int = 24):
    """Get resource usage history"""
    client = create_client_from_config()
    stats = await client.get_resource_usage(hours=hours)
    
    # Transform to chart format
    data = []
    if isinstance(stats, dict) and "cpu" in stats:
        # Parse time series data
        for i, cpu_point in enumerate(stats.get("cpu", [])):
            data.append({
                "timestamp": cpu_point.get("timestamp", ""),
                "cpu": cpu_point.get("value", 0),
                "ram": stats.get("ram", [])[i].get("value", 0) if i < len(stats.get("ram", [])) else 0
            })
    
    return {"data": data}


# Settings snapshots endpoints
@router.get("/settings/snapshots")
async def list_settings_snapshots():
    """List settings snapshots"""
    client = create_client_from_config()
    snapshots = await client.list_settings_sets()
    return {"snapshots": snapshots}


class CreateSnapshotRequest(BaseModel):
    name: str


@router.post("/settings/snapshots/create")
async def create_settings_snapshot(req: CreateSnapshotRequest):
    """Create settings snapshot"""
    client = create_client_from_config()
    success = await client.create_settings_snapshot(name=req.name)
    return {"success": success}


@router.post("/settings/snapshots/{snapshot_id}/restore")
async def restore_settings_snapshot(snapshot_id: int):
    """Restore settings snapshot"""
    client = create_client_from_config()
    success = await client.restore_settings_snapshot(snapshot_id)
    return {"success": success}


@router.delete("/settings/snapshots/{snapshot_id}")
async def delete_settings_snapshot(snapshot_id: int):
    """Delete settings snapshot"""
    client = create_client_from_config()
    success = await client.delete_settings_snapshot(snapshot_id)
    return {"success": success}


# Console endpoints
class ConsoleCommandRequest(BaseModel):
    command: str


@router.post("/console/command")
async def send_console_command(req: ConsoleCommandRequest):
    """Send command to server console"""
    client = create_client_from_config()
    success = await client.send_console_command(req.command)
    return {"success": success, "output": "Command sent"}
