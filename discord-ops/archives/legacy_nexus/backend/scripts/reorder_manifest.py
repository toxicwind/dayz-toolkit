import json
from pathlib import Path

MANIFEST_FILE = Path("backend/patcher/patches/manifest.json")

ORDER = [
    "tony_128",  # Base Overrides (Raw Copies mostly)
    "ezstreet_custom",  # Custom Layouts (New files)
    "vehicles",  # Vehicle Spawns
    "world",  # World Spawns (Foxes, Traders)
    "economy",  # Economy tweaks
    "gameplay",  # Gameplay tweaks (Stamina)
    "core",  # Flags
    "legacy",  # Legacy
    "ezstreet_features",  # Atomic features
]


def main():
    if not MANIFEST_FILE.exists():
        return

    with open(MANIFEST_FILE) as f:
        data = json.load(f)

    patches = data.get("patches", [])

    # Bucketize
    buckets = {k: [] for k in ORDER}
    others = []

    for p in patches:
        cat = p.get("category", "core")
        # Handle some mapping if category names drifted
        if cat in buckets:
            buckets[cat].append(p)
        else:
            # Check if it fits 'ezstreet_features' via filename or desc?
            # Or just put in others
            others.append(p)

    new_list = []
    for k in ORDER:
        # Sort internal to bucket alphabetical for stability
        sorted_bucket = sorted(buckets[k], key=lambda x: x["file"])
        new_list.extend(sorted_bucket)

    # Append others (unknown categories) at the end, sorted
    new_list.extend(sorted(others, key=lambda x: x.get("file", "")))

    data["patches"] = new_list

    with open(MANIFEST_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Reordered {len(new_list)} patches.")


if __name__ == "__main__":
    main()
