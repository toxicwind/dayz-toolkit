"""
Verify ID-based Profiling Logic
Task 9.5
"""

import asyncio
import logging
import sys
from unittest.mock import AsyncMock, Mock

from backend.adm_log_parser import ADMEvent
from backend.analytics import AnalyticsEngine
from backend.database import Database

# Configure Logging
logging.basicConfig(level=logging.INFO)


async def test_analytics_id_logic():
    print("🧪 Testing AnalyticsEngine ID Logic...")

    # Mock Database
    mock_db = Mock(spec=Database)
    mock_db.update_player_profile = AsyncMock()
    mock_db.increment_kill_stats = AsyncMock()
    mock_db.log_combat = AsyncMock()
    mock_db.log_building = AsyncMock()

    analytics = AnalyticsEngine(mock_db)

    # ID's we expect to see
    KILLER_ID = "abc_123_console_id"
    VICTIM_ID = "xyz_987_console_id"
    KILLER_NAME = "Survivor_Badass"
    VICTIM_NAME = "Bambi_Noob"

    # Simulate Combat Event with IDs
    event = ADMEvent(
        timestamp=None,  # Not used in logic check
        event_type="kill",
        player_name=KILLER_NAME,
        player_id=KILLER_ID,
        pos=(100, 0, 100),
        data={
            "attacker_name": KILLER_NAME,
            "attacker_id": KILLER_ID,
            "victim_name": VICTIM_NAME,
            "victim_id": VICTIM_ID,
            "weapon": "M4-A1",
            "dist": 50.0,
        },
    )

    # Process
    print("  -> Processing Combat Event with IDs...")
    analytics.process_event("test_org", event)

    # Allow async tasks to fire (they are fire-and-forget in analytics but we mocked them)
    # Since they are create_task, we might need a small yield if we were running a loop,
    # but with mocks we check call args.

    # Verify DB Calls
    print("  -> Verifying DB Calls...")

    # 1. Profile Updates
    mock_db.update_player_profile.assert_any_call("test_org", KILLER_ID, KILLER_NAME)
    print("     ✅ Killer Profile Updated (by ID)")

    mock_db.update_player_profile.assert_any_call("test_org", VICTIM_ID, VICTIM_NAME)
    print("     ✅ Victim Profile Updated (by ID)")

    # 2. Kill Stats
    mock_db.increment_kill_stats.assert_called_with("test_org", KILLER_ID, VICTIM_ID)
    print("     ✅ Kill Stats Incremented (by ID)")

    # 3. Combat Log
    # check kwargs of log_combat
    _args, kwargs = mock_db.log_combat.call_args
    # call_args is a tuple (args, kwargs)
    # log_combat signature: log_combat(org_id, killer, victim, killer_id, victim_id, ...)
    # checking args or kwargs depending on how it was called. It was called with callbacks in code?
    # No, called with named keywords in analytics.py.

    if kwargs.get("killer_id") == KILLER_ID and kwargs.get("victim_id") == VICTIM_ID:
        print("     ✅ Combat Log persisted with IDs")
    else:
        print(f"     ❌ Combat Log missing IDs! Got: {kwargs}")
        sys.exit(1)

    print("🎉 Verification Successful: Logic uses IDs!")


if __name__ == "__main__":
    asyncio.run(test_analytics_id_logic())
