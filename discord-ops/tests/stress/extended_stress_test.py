#!/usr/bin/env python3
"""Extended stress test with 50 cycles for comprehensive validation"""
import requests
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:18789"

def check_endpoint(name, path, timeout=10):
    try:
        start = time.time()
        res = requests.get(f"{BASE_URL}{path}", timeout=timeout)
        duration = time.time() - start
        if res.status_code == 200:
            print(f"✅ {name:25} OK ({duration:.2f}s)")
            return True, duration
        else:
            print(f"❌ {name:25} FAIL {res.status_code}")
            return False, duration
    except requests.exceptions.Timeout:
        print(f"⏱️  {name:25} TIMEOUT")
        return False, timeout
    except Exception as e:
        print(f"❌ {name:25} ERROR {type(e).__name__}")
        return False, 0

def main():
    cycles = 50
    print(f"Starting {cycles}x Extended End-to-End Stress Test...")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    total_failures = 0
    total_checks = 0
    endpoint_stats = {}
    
    for i in range(1, cycles + 1):
        print(f"\n--- Cycle {i}/{cycles} ---")
        checks = [
            ("Health", "/health"),
            ("Server Status", "/server/status"),
            ("Bot Status", "/bot/status"),
            ("Bot Logs", "/bot/logs?limit=10"),
            ("Economy Config", "/economy/config"),
            ("Gameplay Config", "/config/gameplay"),
            ("Globals Config", "/config/globals"),
            ("Gas Zones", "/config/gas-zones"),
        ]
        
        cycle_fail = False
        for name, path in checks:
            success, duration = check_endpoint(name, path)
            total_checks += 1
            
            if name not in endpoint_stats:
                endpoint_stats[name] = {"success": 0, "fail": 0, "total_time": 0}
            
            if success:
                endpoint_stats[name]["success"] += 1
                endpoint_stats[name]["total_time"] += duration
            else:
                endpoint_stats[name]["fail"] += 1
                cycle_fail = True
                total_failures += 1
        
        if cycle_fail:
            print("⚠️  Cycle encountered errors")
        else:
            print("✅ Cycle completed successfully")
        
        # Brief pause between cycles
        if i < cycles:
            time.sleep(0.5)

    print("\n" + "=" * 80)
    print("FINAL STATISTICS")
    print("=" * 80)
    print(f"Total Checks: {total_checks}")
    print(f"Total Failures: {total_failures}")
    print(f"Success Rate: {((total_checks - total_failures) / total_checks * 100):.2f}%")
    print("\nPer-Endpoint Statistics:")
    print("-" * 80)
    
    for name, stats in sorted(endpoint_stats.items()):
        success_rate = (stats["success"] / (stats["success"] + stats["fail"]) * 100)
        avg_time = stats["total_time"] / stats["success"] if stats["success"] > 0 else 0
        print(f"{name:25} Success: {stats['success']:3}/{stats['success'] + stats['fail']:3} ({success_rate:6.2f}%) Avg: {avg_time:.3f}s")
    
    print("=" * 80)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if total_failures > 0:
        print(f"\n⚠️  Test completed with {total_failures} failures")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")

if __name__ == "__main__":
    main()
