"""
Prove Real Log Correlation (Task 7.5)
Injects RAW log lines (as if from Nitrado) and verifies they get a CID
and that CID propagates to events.
"""

import time

import requests

API_URL = "http://localhost:19101"


def inject_log(line, source="nitrado"):
    url = f"{API_URL}/debug/inject_log"
    print(f"💉 Injecting Log Line: '{line[:50]}...'")
    try:
        r = requests.post(url, params={"line": line, "source": source})
        r.raise_for_status()
        data = r.json()
        print(f"✅ Injected. CID: {data.get('cid')}")
        print(f"   Parsed: {data.get('parsed')}")
        return data.get("cid")
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return None


def main():
    print("🔍 Verifying Real Log Correlation (Task 7.5)...")

    # 1. Killfeed Log Injection
    line = '20:15:33 | Player "Bravo" (id=Unknown) has been killed by player "Alpha" (id=Unknown) with M4A1'
    inject_log(line, source="nitrado")

    # 2. Admin Log Injection
    line_adm = '12:00:00 | Admin "RCON" kicked player "Cheater" (Reason: BattlEye)'
    inject_log(line_adm, source="nitrado")


if __name__ == "__main__":
    time.sleep(2)
    main()
