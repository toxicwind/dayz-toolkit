#!/usr/bin/env python3
import logging
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.config import load_settings
from backend.ftp_client import FTPClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("ftp_deploy")


def deploy_staging_to_ftp():
    settings = load_settings()
    if not settings.ftp_host:
        log.error("FTP details not configured")
        return

    staging_dir = Path("/home/toxic/dayz_workspace/dayz_discord_ops_repo/staging")
    if not staging_dir.exists():
        log.error("Staging directory not found!")
        return

    client = FTPClient(settings.ftp_host, settings.ftp_port, settings.ftp_user, settings.ftp_password)

    try:
        log.info(f"Connecting to EZStreet Nitrado FTP ({settings.ftp_host}) for DEPLOYMENT...")
        client.connect()

        # We need a recursive upload function.
        def upload_recursive(local_path: Path, remote_path: str):
            for item in local_path.iterdir():
                item_remote_path = f"{remote_path}/{item.name}"

                if item.is_dir():
                    # Check if remote dir exists, if not create (if FTPClient supported mkdir, allowing fail if exists)
                    # For now we assume structure largely exists or we fail.
                    # Nitrado structure is static for root folders usually.
                    # We iterate into it
                    upload_recursive(item, item_remote_path)
                else:
                    # Upload file
                    log.info(f"Uploading {item} -> {item_remote_path}")
                    # We use upload_file which does binary upload
                    client.upload_file(str(item), item_remote_path)

        # Deploy dayzxb (Configs)
        # Note local staging structure: staging/dayzxb/...
        log.info("Deploying Configs (/dayzxb)...")
        upload_recursive(staging_dir / "dayzxb", "/dayzxb")

        # Deploy Missions (XMLs)
        # Note local staging structure: staging/dayzxb_missions/...
        log.info("Deploying Missions (/dayzxb_missions)...")
        upload_recursive(staging_dir / "dayzxb_missions", "/dayzxb_missions")

        log.info("Deployment Complete. Initiating Restart Sequence...")

        # Trigger Restart via RCON or API?
        # Nitrado usually requires API restart call for full restart,
        # but changing XMLs often applies instantly or on soft restart.
        # User requested restart (1-3 min window).
        # We need to call the restart endpoint or NitrAPI.

        # For now, we log the intent. Real restart needs token.
        log.warning("SYSTEM PURGE IMMINENT. RESTART TRIGGERED (Simulation).")

    except Exception as e:
        log.error(f"FTP Deployment Failed: {e}")
    finally:
        client._close()


if __name__ == "__main__":
    deploy_staging_to_ftp()
