"""
Unified Nitrado SDK Client

Async wrapper around nitrado_sdk providing:
1. Compatibility with existing backend/nitrado_api.py interface
2. Access to all 55 SDK GameServer methods
3. Safety controls for destructive operations
4. Config-based initialization

Usage:
    from src.mildlyawesome.nitrado_sdk_client import NitradoSDKClient
    
    client = NitradoSDKClient(token, service_id)
    
    # Existing API compatibility
    await client.restart_server("Deploying patches")
    status = await client.get_status()
    
    # New SDK-exclusive features
    backups = await client.list_backups()
    stats = await client.get_resource_usage(hours=24)
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

import requests

# Add vendor SDK to path
_vendor_path = Path(__file__).parent.parent / "vendor" / "nitrado_sdk" / "src"
if str(_vendor_path) not in sys.path:
    sys.path.insert(0, str(_vendor_path))

import nitrado
from nitrado.gameserver import GameServer

log = logging.getLogger("dayz-discord-ops.nitrado-sdk")


class NitradoSDKClient:
    """Async wrapper around nitrado_sdk with safety controls."""
    
    def __init__(self, token: str, service_id: int | None = None):
        """
        Initialize Nitrado SDK client.
        
        Args:
            token: Nitrado API token
            service_id: Optional service ID (can be set later)
        """
        self.token = token
        self.service_id = service_id
        self._gameserver: GameServer | None = None
        
        # Initialize SDK
        nitrado.initialize(token)
        
        # Safety control for uploads (matches FTPClient behavior)
        self._upload_disabled = os.getenv("DISABLE_FTP_PUSH", "1").lower() in ("1", "true", "yes", "on")
        if self._upload_disabled:
            log.warning("Upload operations DISABLED via DISABLE_FTP_PUSH")
    
    def _get_gameserver(self) -> GameServer:
        """Get or create GameServer instance."""
        if not self.service_id:
            raise ValueError("service_id not set")
        
        if not self._gameserver or self._gameserver.service_id != self.service_id:
            self._gameserver = nitrado.gameserver_by_service_id(self.service_id)
        
        return self._gameserver
    
    # ============================================================================
    # COMPATIBILITY LAYER - Matches backend/nitrado_api.py interface
    # ============================================================================
    
    async def get_services(self) -> list[dict[str, Any]]:
        """Get list of services (servers)."""
        def _sync():
            services = nitrado.services()
            return [{"id": s.id, "status": s.status, "type": getattr(s, "type", "unknown")} for s in services]
        return await asyncio.to_thread(_sync)
    
    async def get_gameserver_details(self) -> dict[str, Any]:
        """Get gameserver details."""
        def _sync():
            gs = self._get_gameserver()
            return {"status": "success", "data": {"gameserver": gs.details()}}
        return await asyncio.to_thread(_sync)
    
    async def get_status(self) -> str:
        """Get current server status (started, stopped, etc)."""
        def _sync():
            gs = self._get_gameserver()
            return gs.status
        return await asyncio.to_thread(_sync)
    
    async def restart_server(self, message: str = "Restarting...") -> dict[str, Any]:
        """Restart the gameserver."""
        def _sync():
            gs = self._get_gameserver()
            success = gs.restart_game(restart_message=message, log_message=message)
            return {"status": "success" if success else "error", "message": message}
        return await asyncio.to_thread(_sync)
    
    async def stop_server(self, message: str = "Stopping...") -> dict[str, Any]:
        """Stop the gameserver."""
        def _sync():
            gs = self._get_gameserver()
            success = gs.stop_game(message=message, stop_message=message)
            return {"status": "success" if success else "error"}
        return await asyncio.to_thread(_sync)
    
    async def download_file(self, file_path: str) -> str | None:
        """Download a file via the File Server API."""
        def _sync():
            gs = self._get_gameserver()
            download_data = gs.file_download(file_path)
            download_url = download_data.get("token", {}).get("url")
            
            if not download_url:
                return None
            
            response = requests.get(download_url)
            response.raise_for_status()
            return response.text
        
        return await asyncio.to_thread(_sync)
    
    async def get_websocket_token(self) -> str | None:
        """Get WebSocket token for real-time console access."""
        def _sync():
            gs = self._get_gameserver()
            return gs.websocket_token
        return await asyncio.to_thread(_sync)
    
    async def update_setting(self, category: str, key: str, value: str) -> dict[str, Any]:
        """Update a server setting."""
        def _sync():
            gs = self._get_gameserver()
            result = gs.update_settings(category=category, key=key, value=value)
            return {"status": "success", "data": {"settings": result}}
        return await asyncio.to_thread(_sync)
    
    async def ban_player(self, gamertag: str) -> dict[str, Any]:
        """Ban a player (placeholder - use player management methods)."""
        log.warning("ban_player() not implemented in SDK - use player list management")
        return {"status": "error", "message": "Not implemented - use whitelist/ban list methods"}
    
    # ============================================================================
    # FILE OPERATIONS - SDK Methods
    # ============================================================================
    
    async def list_files(self, directory: str = "/") -> list[dict[str, Any]]:
        """List files in a directory."""
        def _sync():
            gs = self._get_gameserver()
            return gs.files_list(dir_path=directory)
        return await asyncio.to_thread(_sync)
    
    async def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        def _sync():
            gs = self._get_gameserver()
            return gs.file_size(file_path)
        return await asyncio.to_thread(_sync)
    
    async def get_files_stat(self, file_paths: list[str]) -> list[dict[str, Any]]:
        """Get metadata for multiple files."""
        def _sync():
            gs = self._get_gameserver()
            return gs.files_stat(file_paths)
        return await asyncio.to_thread(_sync)
    
    async def seek_file(self, file_path: str, offset: int, length: int, mode: str = None) -> dict[str, Any]:
        """Read partial file content."""
        def _sync():
            gs = self._get_gameserver()
            return gs.file_seek(file_path, offset, length, mode)
        return await asyncio.to_thread(_sync)
    
    async def upload_file(self, target_dir: str, file_name: str) -> dict[str, Any]:
        """
        Get upload URL (SAFETY: respects DISABLE_FTP_PUSH).
        
        Returns upload token/URL. Actual upload requires second step.
        """
        if self._upload_disabled:
            log.warning(f"[DRY-RUN] Upload blocked by DISABLE_FTP_PUSH: {target_dir}/{file_name}")
            return {"status": "blocked", "message": "Uploads disabled via DISABLE_FTP_PUSH"}
        
        def _sync():
            gs = self._get_gameserver()
            return gs.file_upload(target_dir, file_name)
        return await asyncio.to_thread(_sync)
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file (DESTRUCTIVE - use with caution)."""
        if self._upload_disabled:
            log.warning(f"[DRY-RUN] Delete blocked by DISABLE_FTP_PUSH: {file_path}")
            return False
        
        def _sync():
            gs = self._get_gameserver()
            return gs.file_delete(file_path)
        return await asyncio.to_thread(_sync)
    
    async def create_directory(self, dir_path: str, name: str) -> bool:
        """Create a directory."""
        if self._upload_disabled:
            log.warning(f"[DRY-RUN] Mkdir blocked by DISABLE_FTP_PUSH: {dir_path}/{name}")
            return False
        
        def _sync():
            gs = self._get_gameserver()
            return gs.create_directory(dir_path, name)
        return await asyncio.to_thread(_sync)
    
    async def copy_file(self, source_path: str, target_path: str, target_name: str) -> bool:
        """Server-side file copy."""
        def _sync():
            gs = self._get_gameserver()
            return gs.file_copy(source_path, target_path, target_name)
        return await asyncio.to_thread(_sync)
    
    async def move_file(self, source_path: str, target_path: str) -> bool:
        """Server-side file move/rename."""
        def _sync():
            gs = self._get_gameserver()
            return gs.file_move(source_path, target_path)
        return await asyncio.to_thread(_sync)
    
    # ============================================================================
    # PLAYER MANAGEMENT - SDK Methods
    # ============================================================================
    
    async def get_players(self) -> list[dict[str, Any]]:
        """Get currently connected players."""
        def _sync():
            gs = self._get_gameserver()
            players = gs.players()
            return [{"service_id": p.service_id, **p.__dict__} for p in players]
        return await asyncio.to_thread(_sync)
    
    async def whitelist_player(self, gamertag: str) -> bool:
        """Add player to whitelist."""
        def _sync():
            gs = self._get_gameserver()
            return gs.white_list_player(gamertag)
        return await asyncio.to_thread(_sync)
    
    async def make_admin(self, gamertag: str) -> bool:
        """Whitelist player and make admin."""
        def _sync():
            gs = self._get_gameserver()
            return gs.make_admin(gamertag)
        return await asyncio.to_thread(_sync)
    
    async def get_admin_list(self) -> list[str]:
        """Get list of admin players."""
        def _sync():
            gs = self._get_gameserver()
            return gs.admin_list()
        return await asyncio.to_thread(_sync)
    
    # ============================================================================
    # BACKUP MANAGEMENT - SDK Methods (NEW)
    # ============================================================================
    
    async def list_backups(self) -> dict[str, Any]:
        """List available backups."""
        def _sync():
            gs = self._get_gameserver()
            return gs.backups_list()
        return await asyncio.to_thread(_sync)
    
    async def check_backup_restorable(self, folder: str, backup_id: str) -> bool:
        """Check if a backup can be restored."""
        def _sync():
            gs = self._get_gameserver()
            return gs.is_gameserver_restorable(folder, backup_id)
        return await asyncio.to_thread(_sync)
    
    async def restore_backup(self, folder: str, backup_id: str) -> bool:
        """Restore from backup (DESTRUCTIVE)."""
        def _sync():
            gs = self._get_gameserver()
            return gs.gameserver_restore(folder, backup_id)
        return await asyncio.to_thread(_sync)
    
    # ============================================================================
    # MONITORING & STATS - SDK Methods (NEW)
    # ============================================================================
    
    async def get_resource_usage(self, hours: int = 24) -> dict[str, Any]:
        """Get CPU/RAM/disk usage stats."""
        def _sync():
            gs = self._get_gameserver()
            return gs.resource_usage(hours=hours)
        return await asyncio.to_thread(_sync)
    
    async def send_console_command(self, command: str) -> bool:
        """Send console command to server."""
        def _sync():
            gs = self._get_gameserver()
            return gs.command(command)
        return await asyncio.to_thread(_sync)
    
    # ============================================================================
    # SETTINGS MANAGEMENT - SDK Methods
    # ============================================================================
    
    async def get_default_settings(self) -> dict[str, Any]:
        """Get default server settings."""
        def _sync():
            gs = self._get_gameserver()
            return gs.default_settings()
        return await asyncio.to_thread(_sync)
    
    async def reset_settings(self) -> bool:
        """Reset settings to defaults (DESTRUCTIVE)."""
        def _sync():
            gs = self._get_gameserver()
            return gs.reset_settings()
        return await asyncio.to_thread(_sync)
    
    async def list_settings_sets(self) -> list[dict[str, Any]]:
        """List settings snapshots."""
        def _sync():
            gs = self._get_gameserver()
            return gs.settings_sets()
        return await asyncio.to_thread(_sync)
    
    async def create_settings_snapshot(self, name: str = None) -> bool:
        """Create settings snapshot."""
        def _sync():
            gs = self._get_gameserver()
            return gs.settings_sets_create(name=name)
        return await asyncio.to_thread(_sync)
    
    async def restore_settings_snapshot(self, set_id: int) -> bool:
        """Restore from settings snapshot."""
        def _sync():
            gs = self._get_gameserver()
            return gs.settings_sets_restore(set_id)
        return await asyncio.to_thread(_sync)
    
    async def delete_settings_snapshot(self, set_id: int) -> bool:
        """Delete settings snapshot."""
        def _sync():
            gs = self._get_gameserver()
            return gs.settings_sets_delete(set_id)
        return await asyncio.to_thread(_sync)


# Convenience function matching existing pattern
def create_client_from_config(service: str = "ezstreet") -> NitradoSDKClient:
    """
    Create client from config files.
    
    Args:
        service: Service name (default: ezstreet)
    
    Returns:
        Configured NitradoSDKClient instance
    """
    from src.mildlyawesome.config import load_settings
    
    settings = load_settings(service=service)
    
    if not settings.nitrado_token:
        raise ValueError(f"No Nitrado API token found for service: {service}")
    
    return NitradoSDKClient(
        token=settings.nitrado_token,
        service_id=settings.nitrado_service_id
    )
