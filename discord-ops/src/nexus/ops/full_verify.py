#!/usr/bin/env python3
import subprocess
import json
import time
import sys
from pathlib import Path
import asyncio

# Repo root
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from bot.config import load_settings
from bot.a2s_query import query_info
from bot.nitrado_api import NitradoAPIClient

settings = load_settings()

def run_probe(script_name):
    try:
        cmd = [sys.executable, f"tools/{script_name}"]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root)
        # Parse last line as JSON if possible, else return stdout
        lines = res.stdout.strip().split('\n')
        last_line = lines[-1] if lines else "{}"
        try:
            data = json.loads(last_line)
            return data, res.stdout
        except:
            return {"status": "error", "evidence": "Failed to parse JSON output"}, res.stdout
    except Exception as e:
        return {"status": "error", "evidence": str(e)}, ""

def check_a2s():
    try:
        info = query_info(settings.dayz_host, 11603) # Hardcoded query port
        return {
            "status": "success", 
            "evidence": f"Name={info.name}, Map={info.map}, Players={info.players}"
        }
    except Exception as e:
        return {"status": "failed", "evidence": str(e)}

async def restart_cycle():
    client = NitradoAPIClient(settings.nitrado_token)
    service_id = settings.nitrado_service_id
    
    print(">>> TRIGGERING RESTART...")
    await asyncio.to_thread(client.restart_server, service_id)
    
    print(">>> WAITING FOR DOWNTIME (A2S Failure)...")
    down_detected = False
    for i in range(30): # Wait up to 5 mins for it to go down? usually faster
        a2s = check_a2s()
        if a2s['status'] == 'failed':
            print(f"OK: Server Down detected at attempt {i+1}")
            down_detected = True
            break
        time.sleep(10)
        print(".", end="", flush=True)
    
    if not down_detected:
        print("WARNING: Server did not go down in time or A2S is cached?")
        
    print("\n>>> WAITING FOR UP (A2S Success)...")
    up_detected = False
    for i in range(60): # Wait up to 10 mins for boot
        a2s = check_a2s()
        if a2s['status'] == 'success':
            print(f"OK: Server UP detected at attempt {i+1}")
            up_detected = True
            break
        time.sleep(10)
        print(".", end="", flush=True)
        
    return down_detected and up_detected

def main():
    print("=== PHASE 1: PRE-RESTART SNAPSHOT ===")
    
    # 1. A2S
    a2s_res = check_a2s()
    print(f"A2S: {a2s_res}")
    
    # 2. LOGS
    print("Running Logs Probe...")
    logs_data, logs_raw = run_probe("logs_debug_probe.py")
    print(logs_raw)
    
    snapshot_1 = {
        "a2s": a2s_res,
        "logs": logs_data.get('evidence', {})
    }
    
    # RESTART
    restart_ok = asyncio.run(restart_cycle())
    
    print("\n=== PHASE 2: POST-RESTART SNAPSHOT ===")
    # Re-run probes
    a2s_res_2 = check_a2s()
    logs_data_2, logs_raw_2 = run_probe("logs_debug_probe.py")
    print(logs_raw_2)
    
    snapshot_2 = {
        "a2s": a2s_res_2,
        "logs": logs_data_2.get('evidence', {})
    }
    
    # ANALYSIS
    final_verdict = "UNKNOWN"
    
    online = a2s_res_2['status'] == 'success'
    logs_ok = logs_data_2.get('status') == 'success'
    
    # Check if logs changed (simple check: different snippet or different timestamp if we had it)
    # Be lenient for now, seeing files is enough.
    
    if not online:
        final_verdict = "OFFLINE"
    elif not logs_ok:
        final_verdict = "ONLINE + LOGS_MISSING"
    else:
        final_verdict = "ONLINE + LOGS_OK"
            
    summary = {
        "restart_success": restart_ok,
        "snapshot_pre": snapshot_1,
        "snapshot_post": snapshot_2,
        "verdict": final_verdict
    }
    
    print("\n\n====== FINAL SUMMARY JSON ======")
    print(json.dumps(summary, indent=2))
    print("================================")
    print(final_verdict)

if __name__ == "__main__":
    main()
