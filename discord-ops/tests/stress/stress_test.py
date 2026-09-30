#!/usr/bin/env python3
import requests
import time
import sys

BASE_URL = "http://localhost:18789"  # NOTE: Updated port

def check_endpoint(name, path):
    try:
        start = time.time()
        res = requests.get(f"{BASE_URL}{path}", timeout=5)
        duration = time.time() - start
        if res.status_code == 200:
            print(f"✅ {name:20} OK ({duration:.2f}s)")
            return True
        else:
            print(f"❌ {name:20} FAIL {res.status_code}")
            return False
    except Exception as e:
        print(f"❌ {name:20} ERROR {e}")
        return False

def main():
    print("Starting 20x End-to-End Stress Test...")
    cycles = 20
    failures = 0
    
    for i in range(1, cycles + 1):
        print(f"\n--- Cycle {i}/{cycles} ---")
        checks = [
            ("Health", "/health"),
            ("Server Status", "/server/status"),
            ("Bot Status", "/bot/status"),
            ("Bot Logs", "/bot/logs?limit=10"),
            ("Economy Config", "/economy/config"),
            ("Gameplay Config", "/config/gameplay"),
            # ("Nitrado Logs", "/nitrado/logs"), # Might be slow/fail if API is unstable, check carefully
        ]
        
        cycle_fail = False
        for name, path in checks:
            if not check_endpoint(name, path):
                cycle_fail = True
                failures += 1
        
        if cycle_fail:
            print("⚠️  Cycle encountered errors")
        
        time.sleep(1) # Brief pause between cycles

    print(f"\nTest Complete. Total Failures: {failures}")
    if failures > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
