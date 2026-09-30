import os
import shutil
import logging
from pathlib import Path

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Paths
WORKSPACE_ROOT = Path("/home/toxic/dayz_workspace/dayz_discord_ops_repo")
DUMP_DIR = WORKSPACE_ROOT / "backend_data/ftp_base"
STAGING_DIR = WORKSPACE_ROOT / "backend_data/staging"

def init_staging():
    """Clones the FTP Dump to Staging area."""
    if not DUMP_DIR.exists():
        log.error(f"Dump directory not found at {DUMP_DIR}. Run dump_ftp.py first.")
        return False
    
    if STAGING_DIR.exists():
        log.info("Cleaning existing staging area...")
        shutil.rmtree(STAGING_DIR)
    
    log.info(f"Cloning {DUMP_DIR} -> {STAGING_DIR}...")
    shutil.copytree(DUMP_DIR, STAGING_DIR)
    return True

def apply_heist_branding():
    """Overwrites configuration files with aggressive 'Payday' branding."""
    
    # 1. Locate messages.xml (Heuristically find it deep in the structure)
    # It's usually in /dayzxb_missions/dayzOffline.chernarusplus/db/messages.xml
    # But since we dump root, we can search for it.
    
    messages_files = list(STAGING_DIR.rglob("messages.xml"))
    
    if not messages_files:
        log.warning("No messages.xml found in staging to patch.")
        return

    heist_messages_content = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<messages>
    <!-- RESTART WARNINGS: AGGRESSIVE -->
    <message>
        <deadline>600</deadline>
        <shutdown>1</shutdown>
        <text>SYSTEM PURGE IMMINENT. 10 MINUTES UNTIL BLACKOUT. SECURE THE BAG.</text>
    </message>
    <message>
        <deadline>300</deadline>
        <shutdown>1</shutdown>
        <text>5 MINUTES. EXTRACT OR LOSE IT ALL. NO EXCEPTIONS.</text>
    </message>
    <message>
        <deadline>60</deadline>
        <shutdown>1</shutdown>
        <text>FINAL WARNING. 60 SECONDS TO DARKNESS. GET OUT NOW.</text>
    </message>

    <!-- WELCOME / STATUS -->
    <message>
        <delay>5</delay>
        <onconnect>1</onconnect>
        <text>WELCOME TO THE HEIST. TRUST NO ONE. SECURE THE ASSETS.</text>
    </message>

    <!-- RECURRING ALERTS -->
    <message>
        <repeat>20</repeat>
        <text>DISCORD.GG/EZSTREET :: THE ONLY SAFE HOUSE. CHECK COMMS FOR JOBS.</text>
    </message>
    <message>
        <repeat>45</repeat>
        <text>HIGH VALUE TARGETS MARKED. CHECK THE MAP. IT'S PAYDAY.</text>
    </message>
</messages>
"""
    
    for msg_file in messages_files:
        log.info(f"PATCHING IDENTITY: {msg_file}")
        with open(msg_file, "w") as f:
            f.write(heist_messages_content)

    log.info("✅ 'Payday' Aggression Branding Applied.")

if __name__ == "__main__":
    log.info(">>> INITIATING IDENTITY PATCH: EZSTREET (PAYDAY) <<<")
    if init_staging():
        apply_heist_branding()
        log.info(">>> STAGING READY FOR DEPLOYMENT <<<")
        log.info("Run 'python3 bot/scripts/deploy_to_ftp.py' to push to Live.")
