import json
from pathlib import Path

PATCHES_DIR = Path("backend/patcher/patches")


def main():
    print("--- Fixing JSON Source Paths ---")
    for json_file in PATCHES_DIR.glob("*.json"):
        if json_file.name == "manifest.json":
            continue

        try:
            with open(json_file) as f:
                content = json.load(f)

            changed = False
            for key in ["source", "patch_file", "data_file"]:
                if key in content:
                    val = content[key]

                    p = Path(val)
                    filename = p.name
                    # Check if flat file exists
                    flat_path = PATCHES_DIR / filename
                    if flat_path.exists():
                        new_val = f"backend/patcher/patches/{filename}"
                        print(f"[{json_file.name}] Fixing {key}: {val} -> {new_val}")
                        content[key] = new_val
                        changed = True
                    else:
                        # Try with prefix flat names?
                        # e.g. tony_128_events.xml
                        # My consolidation script might have renamed it.
                        # But let's assume simple flatten first.
                        pass

            if changed:
                with open(json_file, "w") as f:
                    json.dump(content, f, indent=4)

        except Exception as e:
            print(f"Error processing {json_file}: {e}")


if __name__ == "__main__":
    main()
