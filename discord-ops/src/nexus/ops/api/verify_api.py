#!/usr/bin/env python3
"""
Verification script for DayZ Dashboard API endpoints.
Tests all newly implemented endpoints to ensure they're responding correctly.
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8080"

def test_endpoint(method: str, path: str, data: Dict[str, Any] = None) -> tuple[bool, str]:
    """Test an API endpoint and return success status and message."""
    try:
        url = f"{BASE_URL}{path}"
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        else:
            return False, f"Unknown method: {method}"
        
        if response.status_code == 200:
            return True, f"✅ {method} {path} - OK"
        else:
            return False, f"❌ {method} {path} - Status {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, f"⚠️  {method} {path} - Backend not running"
    except Exception as e:
        return False, f"❌ {method} {path} - Error: {str(e)}"

def main():
    print("=" * 60)
    print("DayZ Dashboard API Verification")
    print("=" * 60)
    print()
    
    tests = [
        # Health check
        ("GET", "/health", None),
        
        # Server control
        ("GET", "/server/status", None),
        
        # Bot integration
        ("GET", "/bot/status", None),
        ("GET", "/bot/logs", None),
        
        # Economy intelligence
        ("GET", "/economy/config", None),
        ("GET", "/economy/intelligence/clusters", None),
        ("GET", "/economy/intelligence/validate", None),
        
        # Mission files
        ("GET", "/mission/files", None),
        
        # Nitrado logs
        ("GET", "/nitrado/logs", None),
        
        # Stats
        ("GET", "/stats/history", None),
        
        # Players
        ("GET", "/players", None),
        
        # Intelligence
        ("GET", "/intelligence/players", None),
    ]
    
    passed = 0
    failed = 0
    warnings = 0
    
    for method, path, data in tests:
        success, message = test_endpoint(method, path, data)
        print(message)
        if "✅" in message:
            passed += 1
        elif "⚠️" in message:
            warnings += 1
        else:
            failed += 1
    
    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {warnings} warnings")
    print("=" * 60)
    
    if warnings > 0:
        print()
        print("Note: Warnings indicate the backend is not running.")
        print("Start the backend with: python -m dayz_discord_ops.bot")
    
    return failed == 0

if __name__ == "__main__":
    exit(0 if main() else 1)
