#!/usr/bin/env python3
"""
Regenerate Locked Containers ObjectSpawner.
Canonical "Regen" step for DayZ Discord Ops.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONVERTER = REPO_ROOT / "backend" / "scripts" / "dayz_to_objectspawner.py"
# Source: the curated input file
SOURCE = REPO_ROOT / "staging_curated" / "server" / "ezstreet" / "EZStreet_Containers.json"
# Target: the deployable resource
TARGET = REPO_ROOT / "backend" / "patcher" / "resources" / "custom" / "locked_containers_objectspawner.json"


def main():
    if not SOURCE.exists():
        print(f"Error: Source file {SOURCE} not found.")
        sys.exit(1)

    print(f"Regenerating {TARGET.name} from {SOURCE.name}...")

    cmd = [sys.executable, str(CONVERTER), str(SOURCE), str(TARGET)]

    try:
        subprocess.run(cmd, check=True)
        print("OK: Regeneration complete.")
    except subprocess.CalledProcessError as e:
        print(f"FAIL: Regeneration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
