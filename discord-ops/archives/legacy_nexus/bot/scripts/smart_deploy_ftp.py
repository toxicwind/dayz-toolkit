#!/usr/bin/env python3
"""
Smart FTP Deploy with SHA256 Hash Diffing
Only uploads files that have changed (hash mismatch).
Maintains a manifest of deployed hashes for comparison.
"""
import os
import sys
import json
import hashlib
import logging
import time
from pathlib import Path
from typing import Dict, Set

sys.path.append(str(Path(__file__).parent.parent.parent))

from bot.config import load_settings
from bot.ftp_client import FTPClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("smart_deploy")

MANIFEST_FILE = Path("/home/toxic/dayz_workspace/dayz_discord_ops_repo/backend_data/deploy_manifest.json")
STAGING_DIR = Path("/home/toxic/dayz_workspace/dayz_discord_ops_repo/backend_data/staging")

def sha256_file(path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def load_manifest() -> Dict[str, str]:
    """Load the deployment manifest (path -> hash)."""
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_manifest(manifest: Dict[str, str]):
    """Save the deployment manifest."""
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_FILE, 'w') as f:
        json.dump(manifest, f, indent=2)

def scan_staging() -> Dict[str, str]:
    """Scan staging directory and compute hashes for all files."""
    hashes = {}
    for path in STAGING_DIR.rglob('*'):
        if path.is_file():
            rel_path = str(path.relative_to(STAGING_DIR))
            hashes[rel_path] = sha256_file(path)
    return hashes

def diff_manifests(old: Dict[str, str], new: Dict[str, str]) -> Dict[str, Set[str]]:
    """Compute diff between old and new manifests."""
    old_keys = set(old.keys())
    new_keys = set(new.keys())
    
    added = new_keys - old_keys
    removed = old_keys - new_keys
    common = old_keys & new_keys
    
    modified = {k for k in common if old[k] != new[k]}
    unchanged = common - modified
    
    return {
        'added': added,
        'removed': removed,
        'modified': modified,
        'unchanged': unchanged
    }

class SmartFTPDeployer:
    def __init__(self, settings):
        self.settings = settings
        self.client = FTPClient(settings.ftp_host, settings.ftp_port, settings.ftp_user, settings.ftp_password)
        self.stats = {'uploaded': 0, 'skipped': 0, 'failed': 0, 'removed': 0}
    
    def connect(self):
        self.client.connect()
        log.info(f"Connected to FTP: {self.settings.ftp_host}")
    
    def upload_file(self, local_path: Path, remote_path: str) -> bool:
        try:
            # Ensure remote directory exists
            remote_dir = '/'.join(remote_path.split('/')[:-1])
            if remote_dir:
                try:
                    self.client._ftp.mkd(remote_dir)
                except:
                    pass  # Directory may already exist
            
            with open(local_path, 'rb') as f:
                self.client._ftp.storbinary(f"STOR {remote_path}", f)
            return True
        except Exception as e:
            log.error(f"Upload failed {local_path} -> {remote_path}: {e}")
            return False
    
    def smart_deploy(self):
        """Deploy only changed files using hash comparison."""
        log.info("=== SMART FTP DEPLOY (Hash-Diff Mode) ===")
        start_time = time.time()
        
        # Load old manifest
        old_manifest = load_manifest()
        log.info(f"Loaded manifest with {len(old_manifest)} entries")
        
        # Scan current staging
        new_manifest = scan_staging()
        log.info(f"Scanned staging: {len(new_manifest)} files")
        
        # Compute diff
        diff = diff_manifests(old_manifest, new_manifest)
        
        log.info(f"DIFF: +{len(diff['added'])} new, ~{len(diff['modified'])} modified, -{len(diff['removed'])} removed, ={len(diff['unchanged'])} unchanged")
        
        # Connect to FTP
        self.connect()
        
        # Upload new and modified files
        to_upload = diff['added'] | diff['modified']
        for rel_path in sorted(to_upload):
            local_path = STAGING_DIR / rel_path
            remote_path = f"/{rel_path}"
            
            log.info(f"UPLOADING: {rel_path}")
            if self.upload_file(local_path, remote_path):
                self.stats['uploaded'] += 1
            else:
                self.stats['failed'] += 1
        
        # Skip unchanged
        self.stats['skipped'] = len(diff['unchanged'])
        
        # Handle removed files (optional - delete from server)
        for rel_path in diff['removed']:
            log.warning(f"REMOVED in staging (not deleting from server): {rel_path}")
            self.stats['removed'] += 1
        
        # Save updated manifest
        save_manifest(new_manifest)
        
        duration = time.time() - start_time
        log.info(f"=== DEPLOY COMPLETE in {duration:.2f}s ===")
        log.info(f"Stats: Uploaded={self.stats['uploaded']}, Skipped={self.stats['skipped']}, Failed={self.stats['failed']}")
        
        self.client._close()
        return self.stats

if __name__ == "__main__":
    settings = load_settings()
    deployer = SmartFTPDeployer(settings)
    deployer.smart_deploy()
