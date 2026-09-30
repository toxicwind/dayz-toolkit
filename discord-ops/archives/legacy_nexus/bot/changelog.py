import logging
import asyncio
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import difflib

import discord

log = logging.getLogger("dayz-discord-ops.engagement")

@dataclass
class FileChange:
    file_path: str
    change_type: str  # 'modified', 'created', 'deleted'
    diff_lines: List[str]
    changed_by: str
    timestamp: datetime

class ChangeLogManager:
    """
    Monitors server configuration files and posts aesthetic change notifications.
    Implements the 'Change Log Feed' engagement feature.
    """
    
    def __init__(self, bot: discord.Client, channel_id: int, watch_paths: List[str]):
        self.bot = bot
        self.channel_id = channel_id
        self.watch_paths = [Path(p) for p in watch_paths]
        self._file_hashes: Dict[str, str] = {}
        self._running = False
        
    async def start(self):
        """Start monitoring files for changes"""
        self._running = True
        # Initial scan
        await self._scan_files()
        # Start periodic check
        asyncio.create_task(self._watch_loop())
        log.info(f"ChangeLogManager started, watching {len(self.watch_paths)} paths")
        
    async def stop(self):
        self._running = False
        
    async def _watch_loop(self):
        """Periodic file check (every 60 seconds)"""
        while self._running:
            await asyncio.sleep(60)
            await self._scan_files()
            
    async def _scan_files(self):
        """Scan all watched paths for changes"""
        for watch_path in self.watch_paths:
            if not watch_path.exists():
                continue
                
            if watch_path.is_file():
                await self._check_file(watch_path)
            elif watch_path.is_dir():
                # Recursively check all XML/JSON files
                for file_path in watch_path.rglob("*.xml"):
                    await self._check_file(file_path)
                for file_path in watch_path.rglob("*.json"):
                    await self._check_file(file_path)
                    
    async def _check_file(self, file_path: Path):
        """Check if a file has changed"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            current_hash = hashlib.md5(content.encode()).hexdigest()
            
            file_key = str(file_path)
            previous_hash = self._file_hashes.get(file_key)
            
            if previous_hash is None:
                # First time seeing this file
                self._file_hashes[file_key] = current_hash
                return
                
            if current_hash != previous_hash:
                # File changed!
                log.info(f"Detected change in {file_path.name}")
                
                # Generate diff (simplified - just show it changed)
                change = FileChange(
                    file_path=str(file_path),
                    change_type='modified',
                    diff_lines=[f"File modified: {file_path.name}"],
                    changed_by="System",  # Could be enhanced with git blame
                    timestamp=datetime.now()
                )
                
                await self._post_change(change)
                self._file_hashes[file_key] = current_hash
                
        except Exception as e:
            log.error(f"Error checking file {file_path}: {e}")
            
    async def _post_change(self, change: FileChange):
        """Post a change notification to Discord"""
        try:
            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                channel = await self.bot.fetch_channel(self.channel_id)
            if not channel:
                log.error(f"Change log channel {self.channel_id} not found")
                return
                
            # Create aesthetic embed
            embed = discord.Embed(
                title="📝 Server Configuration Updated",
                color=0x00D9FF,  # Cyan
                timestamp=change.timestamp
            )
            
            file_name = Path(change.file_path).name
            embed.add_field(
                name="File",
                value=f"`{file_name}`",
                inline=True
            )
            
            embed.add_field(
                name="Type",
                value=change.change_type.capitalize(),
                inline=True
            )
            
            embed.add_field(
                name="Changed By",
                value=change.changed_by,
                inline=True
            )
            
            # Add diff preview (first 5 lines)
            if change.diff_lines:
                diff_preview = "\n".join(change.diff_lines[:5])
                if len(change.diff_lines) > 5:
                    diff_preview += f"\n... and {len(change.diff_lines) - 5} more changes"
                embed.add_field(
                    name="Changes",
                    value=f"```diff\n{diff_preview[:1000]}\n```",
                    inline=False
                )
            
            embed.set_footer(text="Server Updates • Real-time monitoring")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            log.exception(f"Failed to post change notification: {e}")

# Global instance
_changelog_manager: Optional[ChangeLogManager] = None

def get_changelog_manager() -> Optional[ChangeLogManager]:
    return _changelog_manager

def init_changelog_manager(bot: discord.Client, channel_id: int, watch_paths: List[str]):
    global _changelog_manager
    _changelog_manager = ChangeLogManager(bot, channel_id, watch_paths)
    return _changelog_manager
