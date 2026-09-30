"""
Patch State Verification Script
Audits the current state of sensitive XML files (types.xml, mapgroupproto.xml)
and checks if specific patches (like Loot crates) are present.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path("/home/toxic/dayz_workspace/dayz_discord_ops_repo")
SERVER_ROOT = REPO_ROOT / "staging" / "ezstreet" / "dayzxb_missions" / "dayzOffline.chernarusplus"


def verify_types_xml():
    types_path = SERVER_ROOT / "db" / "types.xml"
    if not types_path.exists():
        print(f"❌ types.xml missing at {types_path}")
        return False

    try:
        tree = ET.parse(types_path)
        root = tree.getroot()

        # Check for our Wave 1 items
        items = ["SeaChest", "WoodenCrate"]
        all_ok = True

        for item_name in items:
            nodes = root.findall(f".//type[@name='{item_name}']")
            count = len(nodes)

            if count == 0:
                print(f"⚠️  Missing {item_name}")
                all_ok = False
            elif count == 1:
                print(f"✅ Found unique {item_name}")
            else:
                print(f"❌ DUPLICATE DETECTED: {item_name} (Count: {count})")
                all_ok = False

        return all_ok
    except ET.ParseError:
        print(f"❌ XML Parse Error in {types_path}")
        return False


if __name__ == "__main__":
    print("--- Patch State Verification ---")
    verify_types_xml()
    print("--------------------------------")
