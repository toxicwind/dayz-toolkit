#!/usr/bin/env python3
import sys
import logging
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from bot.config import load_settings
from bot.ftp_client import FTPClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("ftp_list")

def list_ftp_structure():
    settings = load_settings()
    if not settings.ftp_host:
        return

    client = FTPClient(settings.ftp_host, settings.ftp_port, settings.ftp_user, settings.ftp_password)

    try:
        log.info(f"Connecting to {settings.ftp_host}...")
        client.connect()
        
        log.info("Listing root /...")
        items = client.list_files("/")
        for item in items:
            name = item['name']
            raw = item.get('raw', '').strip()
            log.info(f"Root item: {name} (Raw: {raw})")
            
            # If directory, list its content
            if item.get('type') == 'dir' or raw.startswith('d'):
                 try:
                     sub_path = f"/{name}"
                     log.info(f"Scanning {sub_path}...")
                     sub_items = client.list_files(sub_path)
                     for sub in sub_items:
                         log.info(f"  - {sub['name']}")
                 except Exception as e:
                     log.error(f"Failed to scan {sub_path}: {e}")

    except Exception as e:
        log.error(f"FTP List Failed: {e}")
    finally:
        client._close()

if __name__ == "__main__":
    list_ftp_structure()
