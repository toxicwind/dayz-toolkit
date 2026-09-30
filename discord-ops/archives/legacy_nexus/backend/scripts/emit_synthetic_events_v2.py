"""
Synthetic Event Emitter (Proof of Source)
Injects events via API -> EventBus -> LogStreamer/Discord.
"""

import time

import requests

API_URL = "http://localhost:18790"


def emit(event_type, payload):
    url = f"{API_URL}/debug/emit_event"
    print(f"Injecting {event_type}...")
    try:
        r = requests.post(url, params={"event_type": event_type}, json=payload)
        r.raise_for_status()
        print(f"✅ OK: {r.json()}")
    except Exception as e:
        print(f"❌ FAIL: {e}")


def main():
    print("🔥 Firing Synthetic Events into Fabric...")

    # 1. Killfeed Event
    emit(
        "killfeed.kill",
        {
            "timestamp": datetime.utcnow().isoformat(),
            "killer": "SyntheticSurvivor",
            "victim": "TargetDummy",
            "weapon": "M4-A1",
            "distance": 150.5,
            "location": "NWAF",
        },
    )

    # 2. Admin Event
    emit(
        "admin.action",
        {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "Global Ban",
            "admin": "AutoAdmin",
            "reason": "Hacking Violation (Synthetic)",
        },
    )

    # 3. Status Tick (simulated)
    # emit("status.tick", {"players": 50, "max": 60})


if __name__ == "__main__":
    from datetime import datetime

    time.sleep(2)  # Give WS listener time to connect
    main()
