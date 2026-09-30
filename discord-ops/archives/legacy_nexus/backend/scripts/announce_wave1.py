"""
Announce Wave 1 Patches to Discord
Task 10 Verification
"""

import sys

import requests

API_URL = "http://localhost:19101"


def announce():
    print("🚀 Triggering Patch Announcement...")

    payload = {
        "title": "Operation Hardening (Wave 1)",
        "version": "1.28-SIGMA.1",
        "description": "Applied critical hardening patches for gameplay and consistency.",
        "changes": [
            "Fixed Animal Max Count (Globals.xml)",
            "Standardized Restock Times (0 -> 3600s)",
            "Applied Gameplay config adjustments (cfggameplay.json)",
            "Enforced correlation IDs on all logs",
            "Improved Discord connectivity resilience",
        ],
    }

    try:
        url = f"{API_URL}/ops/announce_patch"
        res = requests.post(url, json=payload)
        res.raise_for_status()
        print(f"✅ Success: {res.json()}")
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    announce()
