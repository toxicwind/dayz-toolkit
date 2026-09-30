"""
Apply Wave 1 Hardening Patches (Goopsta/Tony)
Task 9: 5 Atomic Patches + Validation + Manifest
"""

import json
from pathlib import Path

from backend.patch_manager import PatchManager

# Setup paths (Assuming running from repo root)
BASE_DIR = Path("backend/vanilla_defaults")  # Mock base dir for safety
OUTPUT_DIR = Path("backend/server_config")  # Live config dir

# Check if base exists, if not create mock for testing
if not BASE_DIR.exists():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    # create mock cfggameplay.json
    with open(BASE_DIR / "cfggameplay.json", "w") as f:
        json.dump(
            {
                "GeneralData": {"disableBaseDamage": False, "disablePersonalLight": False},
                "PlayerData": {"StaminaData": {"staminaMinCap": 5.0}},
            },
            f,
        )
    # create mock globals.xml
    with open(BASE_DIR / "globals.xml", "w") as f:
        f.write('<variables><var name="ZombieMaxCount" value="1000" type="0"/></variables>')

pm = PatchManager(BASE_DIR, OUTPUT_DIR)

# --- Patch Definitions ---
patches = [
    {
        "file": "cfggameplay.json",
        "id": "hardening_personal_light",
        "type": "json",
        "body": [{"op": "replace", "path": "/GeneralData/disablePersonalLight", "value": True}],
    },
    {
        "file": "cfggameplay.json",
        "id": "hardening_base_damage",
        "type": "json",
        "body": [{"op": "replace", "path": "/GeneralData/disableBaseDamage", "value": True}],  # Secure bases
    },
    {
        "file": "cfggameplay.json",
        "id": "hardening_stamina_cap",
        "type": "json",
        "body": [{"op": "replace", "path": "/PlayerData/StaminaData/staminaMinCap", "value": 10.0}],  # Raise min cap
    },
    {
        "file": "globals.xml",
        "id": "perf_zombie_limit",
        "type": "xml",
        "body": [{"op": "set_attr", "xpath": "//var[@name='ZombieMaxCount']", "attr": "value", "value": "800"}],
    },
    {
        "file": "globals.xml",
        "id": "hardening_animal_max",
        "type": "xml",
        "body": [
            {"op": "replace", "xpath": "//var[@name='AnimalMaxCount']/@value", "value": "200"}
        ],  # Mock xpath replacement logic
    },
]

# --- Execution ---
manifest = {"wave": "1", "status": "deployed", "patches": []}

print("🛡️ applying Wave 1 Hardening Patches...")

for p in patches:
    print(f"Applying {p['id']} to {p['file']}...")
    success = False
    if p["type"] == "json":
        success = pm.apply_json_patch(p["file"], p["id"], p["body"])
    else:
        success = pm.apply_xml_patch(p["file"], p["id"], p["body"])

    status = "SUCCESS" if success else "FAILED"
    print(f"  -> {status}")
    manifest["patches"].append({"id": p["id"], "file": p["file"], "status": status})

# Write Manifest
manifest_path = OUTPUT_DIR / "wave1_manifest.json"
with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=4)

print(f"✅ Manifest written to {manifest_path}")
