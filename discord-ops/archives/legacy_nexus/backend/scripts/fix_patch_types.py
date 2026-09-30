import json
from pathlib import Path

PATCHES_DIR = Path("backend/patcher/patches")


def main():
    print("--- Checking for missing 'type' in cfggameplay patches ---")
    count = 0
    for json_file in PATCHES_DIR.glob("*.json"):
        if json_file.name == "manifest.json":
            continue

        try:
            with open(json_file) as f:
                data = json.load(f)

            # Heuristic: If it targets cfggameplay.json and has 'values' or 'path', it's a merge/patch.
            if data.get("target") == "cfggameplay.json" and "type" not in data:
                if "values" in data or "path" in data:
                    print(f"[{json_file.name}] Missing 'type'. Adding 'json_merge'.")
                    data["type"] = "json_merge"

                    with open(json_file, "w") as f:
                        json.dump(data, f, indent=4)
                    count += 1
                else:
                    print(f"[{json_file.name}] Targets cfggameplay but no values/path? content: {data.keys()}")

        except Exception as e:
            print(f"Error processing {json_file}: {e}")

    print(f"Fixed {count} patches.")


if __name__ == "__main__":
    main()
