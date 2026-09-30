from pathlib import Path
from src.mildlyawesome.discord_registry import DiscordRegistry
import sys

root = Path(".").resolve()
print(f"Root: {root}")
reg = DiscordRegistry(root)
sid = reg.resolve("ops.status")
print(f"ops.status -> {sid}")

expected = 1459508528778707111
if sid == expected:
    print("SUCCESS")
    sys.exit(0)
else:
    print(f"FAILURE: Expected {expected}, got {sid}")
    sys.exit(1)

