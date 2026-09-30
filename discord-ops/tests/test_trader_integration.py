#!/usr/bin/env python3
"""
Test script to simulate trader bot integration and verify the complete cycle
"""
import sys
sys.path.insert(0, '/home/toxic/dayz_workspace/dayz_discord_ops_repo/src')

from dayz_discord_ops.database import Database
from dayz_discord_ops.spawn_manager import SpawnManager
from dayz_discord_ops.adm_log_parser import ADMLogParser
from dayz_discord_ops.config import Settings

import json

def test_database():
    """Test database creation and operations"""
    print("=== Testing Database ===")
    
    # Create a minimal settings object
    class MockSettings:
        mysql_host = None  # Set to None to skip real DB
        mysql_port = 3306
        mysql_user = "test"
        mysql_pass = "test"
        mysql_db = "test"
    
    settings = MockSettings()
    db = Database(settings)
    
    print("✓ Database class instantiated")
    print()

def test_log_parser():
    """Test log parsing for coordinates"""
    print("=== Testing Log Parser ===")
    
    # Test with and without coords
    sample_logs = """
2025-12-25 01:00:00 | Player "TestPlayer#1234" (id=ABC123) has been connected
2025-12-25 01:30:00 | Player "TestPlayer#1234" (id=ABC123) has been disconnected (pos=<12345.6, 789.0, 11223.4>)
2025-12-25 02:00:00 | Player "AnotherPlayer" (id=XYZ789) has been disconnected
"""
    
    events = ADMLogParser.parse_log_content(sample_logs)
    
    for event in events:
        if 'pos_x' in event:
            print(f"✓ Parsed disconnect with coords: {event['gamertag']} at ({event['pos_x']}, {event['pos_y']}, {event['pos_z']})")
        else:
            print(f"✓ Parsed {event['event_type']}: {event['gamertag']}")
    
    print()

def test_spawn_manager():
    """Test spawn manager"""
    print("=== Testing Spawn Manager ===")
    
    spawn_mgr = SpawnManager()
    
    # Test coordinates
    test_pos = (12345.6, 789.0, 11223.4)
    test_classname = "M65Jacket_Black"
    test_gamertag = "TestPlayer#1234"
    
    success = spawn_mgr.queue_spawn(test_gamertag, test_classname, test_pos)
    
    if success:
        print(f"✓ Successfully queued spawn of {test_classname} at {test_pos}")
        
        # Verify it was added
        with open(spawn_mgr.missions_path, 'r') as f:
            data = json.load(f)
            last_obj = data['Objects'][-1]
            if last_obj['name'] == test_classname:
                print(f"✓ Verified item in Missions.json: {last_obj['name']} at {last_obj['pos']}")
            else:
                print(f"✗ Item not found in Missions.json")
    else:
        print("✗ Failed to queue spawn")
    
    print()

def test_trader_csv():
    """Test trader CSV loading"""
    print("=== Testing Trader CSV ===")
    
    import csv
    csv_path = "/home/toxic/dayz_workspace/dayz_discord_ops_repo/trader_items_with_classnames.csv"
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    mapped = sum(1 for r in rows if r.get('Classname') and 'No exact match' not in r['Classname'])
    total = len(rows)
    
    print(f"✓ Loaded {total} items from CSV")
    print(f"✓ {mapped} items have valid classnames ({100*mapped//total}%)")
    print(f"  {total - mapped} items need manual mapping")
    
    # Show some examples
    print("\nSample mapped items:")
    count = 0
    for row in rows:
        if row.get('Classname') and 'No exact match' not in row['Classname'] and count < 5:
            print(f"  • {row['Item Name']} → {row['Classname']}")
            count += 1
    
    print()

def main():
    print("=" * 60)
    print("DayZ Trader Bot Integration Test")
    print("=" * 60)
    print()
    
    test_database()
    test_log_parser()
    test_spawn_manager()
    test_trader_csv()
    
    print("=" * 60)
    print("Integration Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
