#!/usr/bin/env python3
"""
DayZ Discord Ops - Single Execution Surface
No random scripts. No .env loading. YAML First.
"""
import sys
import yaml
import json
import time
import subprocess
import requests
import socket
from pathlib import Path
from dataclasses import asdict

# Ensure we can import from bot/
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from bot.config import load_settings, Settings

def log(msg, level="INFO"):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def run_cmd(cmd, cwd=None, ignore_fail=False):
    log(f"EXEC: {cmd}")
    try:
        res = subprocess.run(
            cmd, 
            shell=True, 
            check=not ignore_fail, 
            cwd=cwd or repo_root,
            capture_output=True,
            text=True
        )
        return res
    except subprocess.CalledProcessError as e:
        log(f"FAIL: {e.stderr}", "ERROR")
        if not ignore_fail:
            sys.exit(1)
        return e

def print_config():
    """Print effective configuration (merged)"""
    settings = load_settings()
    # Mask secrets
    data = asdict(settings)
    if data['nitrado']['api_token']: data['nitrado']['api_token'] = "***"
    if data['nitrado']['password']: data['nitrado']['password'] = "***"
    if data['discord']['token']: data['discord']['token'] = "***"
    if data['mysql']['password']: data['mysql']['password'] = "***"
    if data['ftp_password']: data['ftp_password'] = "***"
    
    print(yaml.dump(data, sort_keys=False))

def ensure_compose_up():
    """Ensure Docker Compose is up"""
    log("Checking Docker Compose state...")
    cmd = "docker compose -f compose.yaml ps --format json"
    res = run_cmd(cmd)
    if not res.stdout.strip():
        log("Docker Compose not running. Starting...")
        run_cmd("docker compose -f compose.yaml up -d --build")
    else:
        log("Docker Compose running. Ensuring latest build...")
        run_cmd("docker compose -f compose.yaml up -d --build")

def check_bot_health():
    """Check if bot container is healthy and API reachable"""
    for _ in range(30):
        try:
            res = requests.get("http://localhost:18789/health", timeout=2)
            if res.status_code == 200:
                log("Bot API Verified: HEALTHY")
                return True
        except:
            pass
        time.sleep(1)
        print(".", end="", flush=True)
    log("\nBot API Failed to respond after 30s", "ERROR")
    return False

def burn_in_gauntlet():
    """Run the Burn-In Gauntlet"""
    log("=== STARTING BURN-IN GAUNTLET ===")
    
    checks = {
        "boot": False,
        "api_health": False,
        "ftp_access": False,
        "discord_connect": False
    }

    # 1. Boot Checks
    ensure_compose_up()
    if check_bot_health():
        checks["boot"] = True
        checks["api_health"] = True
    
    # 2. FTP Access Check
    # Trigger log listing via API
    try:
        res = requests.get("http://localhost:18789/logs", timeout=5)
        if res.status_code == 200 and "files" in res.json():
            checks["ftp_access"] = True
            log("FTP Access: PASS")
        else:
            log("FTP Access: FAIL (API Error or Empty)", "WARN")
    except:
        log("FTP Access: FAIL (Req Error)", "WARN")
        
    # 3. Discord Connect (Check Logs)
    # Grep logs for "Logged in as" - use larger window
    cmd = "docker compose -f compose.yaml logs --tail 1000 dayz-discord-bot"
    logs = run_cmd(cmd).stdout
    if "Logged in as" in logs:
        checks["discord_connect"] = True
        log("Discord Connectivity: PASS")
    else:
        log("Discord Connectivity: FAIL (Log verify failed - check logs manually)", "WARN")

    # Save artifact
    proof_path = repo_root / "logs/burnin/checks.json"
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    with open(proof_path, "w") as f:
        json.dump(checks, f, indent=2)
    
    log(f"Burn-in complete. Results saved to {proof_path}")
    
    if all(checks.values()):
        log("Verdict: GREEN", "SUCCESS")
        sys.exit(0)
    else:
        log("Verdict: RED", "FAIL")
        sys.exit(1)

def audit_channels():
    """Audit channels via API"""
    try:
        res = requests.get("http://localhost:18789/audit/channels", timeout=5)
        if res.status_code == 200:
            data = res.json()
            if "status" in data and data["status"] == "error":
                log(f"Audit FAIL: {data['message']}", "ERROR")
                return

            print(json.dumps(data, indent=2))
            
            # Summary
            stats = data.get('stats', {})
            log(f"Audit Complete: {stats.get('total', 0)} channels. {stats.get('matched', 0)} matched, {stats.get('unmatched', 0)} unmatched.")
        else:
            log(f"Audit Request Failed: {res.status_code}", "ERROR")
    except Exception as e:
        log(f"Audit Exception: {e}", "ERROR")

def trigger_emergent_selfplay():
    """Trigger the emergent self-play test via file signal"""
    trigger_path = repo_root / "state/selfplay_trigger.json"
    trigger_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(trigger_path, "w") as f:
        json.dump({"mode": "emergent"}, f)
        
    log("Signals sent: Emergent Self-Play Triggered. Check bot logs.", "SUCCESS")

def main():
    if len(sys.argv) < 2:
        print("Usage: tools/ops.py [config:print | burnin | run:dev | channel:audit | selfplay:emergent]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "config:print":
        print_config()
    elif cmd == "burnin":
        burn_in_gauntlet()
    elif cmd == "run:dev":
        ensure_compose_up()
        run_cmd("docker compose -f compose.yaml logs -f dayz-discord-bot")
    elif cmd == "channel:audit":
        audit_channels()
    elif cmd == "selfplay:emergent":
        trigger_emergent_selfplay()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
