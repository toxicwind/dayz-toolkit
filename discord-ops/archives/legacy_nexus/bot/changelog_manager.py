import os
import hashlib
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime

log = logging.getLogger("dayz-discord-ops.changelog_manager")

class ChangelogManager:
    """
    Tracks changes to mission files and parses CHANGELOG.md for multi-tenant notifications.
    """
    def __init__(self, base_dir: str = "server"):
        self.base_dir = Path(base_dir)
        self.hashes: Dict[str, Dict[str, str]] = {} # org_id -> {file_path: hash}

    async def _get_files_to_track(self, org_id: str) -> List[Path]:
        def _sync_get():
            mission_dir = self.base_dir / org_id / "dayzxb_missions"
            if not mission_dir.exists():
                return []
            extensions = {'.xml', '.json', '.c', '.md'}
            return [p for p in mission_dir.rglob('*') if p.suffix in extensions and p.is_file()]
        return await asyncio.to_thread(_sync_get)

    async def _calculate_hash(self, path: Path) -> str:
        def _sync_hash():
            sha256_hash = hashlib.sha256()
            try:
                with open(path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                return sha256_hash.hexdigest()
            except Exception as e:
                log.warning(f"Could not hash {path}: {e}")
                return ""
        return await asyncio.to_thread(_sync_hash)

    async def scan(self, org_id: str) -> List[str]:
        """
        Scans for changed files and returns a list of modified file names.
        """
        current_files = await self._get_files_to_track(org_id)
        
        if org_id not in self.hashes:
            self.hashes[org_id] = {}
            for p in current_files:
                self.hashes[org_id][str(p)] = await self._calculate_hash(p)
            return []

        changed = []
        current_file_set = {str(p) for p in current_files}
        
        for p in current_files:
            p_str = str(p)
            new_hash = await self._calculate_hash(p)
            if p_str not in self.hashes[org_id] or self.hashes[org_id][p_str] != new_hash:
                changed.append(p.name)
                self.hashes[org_id][p_str] = new_hash
                
        # Check for deletions
        deleted = [Path(p).name for p in self.hashes[org_id] if p not in current_file_set]
        for d in deleted:
            # Clean up missing files from tracking
            # In a more robust implementation, we'd handle keys properly
            pass

        return changed

    async def get_latest_changelog_entry(self, org_id: str) -> Optional[str]:
        """Reads the top section of CHANGELOG.md in the mission directory."""
        def _sync_read():
            changelog_path = self.base_dir / org_id / "dayzxb_missions" / "CHANGELOG.md"
            if not changelog_path.exists():
                changelog_path = Path("CHANGELOG.md")
                if not changelog_path.exists():
                    return None

            try:
                content = changelog_path.read_text(encoding='utf-8')
                lines = content.splitlines()
                entry_lines = []
                capture = False
                for line in lines:
                    if line.startswith("# ") or line.startswith("## "):
                        if capture: break
                        capture = True
                        entry_lines.append(line)
                    elif capture:
                        entry_lines.append(line)
                
                return "\n".join(entry_lines).strip() if entry_lines else None
            except Exception as e:
                log.warning(f"Failed to read changelog for {org_id}: {e}")
                return None
        return await asyncio.to_thread(_sync_read)
