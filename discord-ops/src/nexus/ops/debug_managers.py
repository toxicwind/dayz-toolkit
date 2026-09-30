import sys
import os

print("Starting debug...")
try:
    print("Importing PatchManager...")
    from src.dayz_discord_ops.patch_manager import PatchManager
    print("PatchManager imported.")
    
    print("Importing DayZConfigManager...")
    from src.dayz_discord_ops.dayz_config_manager import DayZConfigManager
    print("DayZConfigManager imported.")
    
    print("Instantiating DayZConfigManager...")
    manager = DayZConfigManager()
    print("DayZConfigManager instantiated.")
    
    print("Testing get_globals...")
    g = manager.get_globals()
    print(f"Globals: {list(g.keys())[:3]}")

except Exception as e:
    print(f"CRASH/ERROR: {e}")
    import traceback
    traceback.print_exc()
