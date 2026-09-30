#!/usr/bin/env python3
"""
Server Backup Script
--------------------
1. Zips the local 'staging' directory (Configuration Snapshot).
2. Connects to FTP and downloads 'storage_1' (Persistence Snapshot).
3. Stores backups in 'backups/' directory.
"""

import datetime
import logging
import os
import sys
import zipfile
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger("backup_server")

# Import project modules
sys.path.append(str(Path(__file__).parent.parent.parent))
from backend.config import load_settings
from backend.ftp_client import FTPClient


def backup_local_staging(backup_dir: Path, staging_dir: Path) -> Path | None:
    if not staging_dir.exists():
        log.warning(f"Staging directory not found: {staging_dir}")
        return None

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = backup_dir / f"config_staging_{timestamp}.zip"

    log.info(f"Zipping staging dir to {zip_path}...")
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _dirs, files in os.walk(staging_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(staging_dir)
                    zipf.write(file_path, arcname)
        log.info("Local configuration backup complete.")
        return zip_path
    except Exception as e:
        log.error(f"Failed to zip staging: {e}")
        return None


def backup_remote_persistence(backup_dir: Path, settings) -> bool:
    if not settings.ftp_host:
        log.warning("FTP not configured. Skipping persistence backup.")
        return False

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    persistence_backup_dir = backup_dir / f"persistence_{timestamp}"

    # Mission Path from settings usually points to valid mission like dayzOffline.chernarusplus
    # Storage is usually inside that, e.g. /dayzxb_missions/dayzOffline.chernarusplus/storage_1
    # Check if 'storage_1' exists? Or just download the mission folder?
    # Downloading entire mission folder might be huge.
    # Let's target 'storage_1' if we can guess the path, otherwise the whole mission.

    remote_path = settings.ftp_mission_path
    if not remote_path:
        log.warning("No mission path configured.")
        return False

    # Assuming 'storage_1' is the standard persistence folder
    target_remote_dir = f"{remote_path}/storage_1"

    log.info(f"Connecting to FTP to download: {target_remote_dir}")

    client = FTPClient(settings.ftp_host, settings.ftp_port, settings.ftp_user, settings.ftp_password)
    try:
        if not client.connect():
            return False

        # Check if dir exists by listing parent?
        # Just try downloading
        success = client.download_tree(target_remote_dir, str(persistence_backup_dir))

        if success:
            log.info(f"Persistence backup complete: {persistence_backup_dir}")
            return True
        else:
            log.error("Persistence backup failed (partial or connect error).")
            return False

    finally:
        client._close()


def main():
    settings = load_settings()
    repo_root = Path(__file__).parent.parent.parent
    staging_dir = repo_root / "staging"
    backup_dir = repo_root / "backups"

    backup_dir.mkdir(exist_ok=True)

    log.info("--- Starting Server Backup ---")

    # 1. Local Config Backup
    backup_local_staging(backup_dir, staging_dir)

    # 2. Remote Persistence Backup
    backup_remote_persistence(backup_dir, settings)

    log.info("--- Backup Process Finished ---")


if __name__ == "__main__":
    main()
