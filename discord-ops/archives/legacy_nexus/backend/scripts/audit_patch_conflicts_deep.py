import json
from collections import defaultdict
from pathlib import Path

PATCHES_DIR = Path("backend/patcher/patches")


def flatten_json(y):
    out = {}

    def flatten(x, name=""):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + ".")
        elif type(x) is list:
            out[name[:-1]] = "LIST_CONTENT_PLACEHOLDER"  # Treat lists as atomic for collision detection for now
        else:
            out[name[:-1]] = x

    flatten(y)
    return out


def main():
    print("=== DEEP PATCH AUDIT ===")

    # Structure: target -> key -> [patch_files]
    collisions = defaultdict(lambda: defaultdict(list))
    # Structure: content_hash -> [patch_files]
    content_map = defaultdict(list)

    patches = list(PATCHES_DIR.glob("*.json"))
    PATCHES_DIR / "manifest.json"

    for p_file in patches:
        if p_file.name == "manifest.json":
            continue

        try:
            with open(p_file) as f:
                data = json.load(f)

            # 1. Check for Duplicate Content (naive string dump)
            content_str = json.dumps(data.get("values", {}), sort_keys=True)
            if content_str != "{}":
                content_map[content_str].append(p_file.name)

            # 2. Key Collision Analysis (for cfggameplay.json)
            target = data.get("target") or data.get("target_file")

            # Heuristic for implicit target
            if not target and "cfggameplay" in p_file.name:
                target = "cfggameplay.json"

            if target == "cfggameplay.json":
                values = data.get("values", {})
                flat = flatten_json(values)

                for key in flat:
                    collisions[target][key].append(p_file.name)

        except Exception as e:
            print(f"Error parsing {p_file.name}: {e}")

    # REPORTING
    print("\n[!] DUPLICATE VALUES (Redundant Patches):")
    for _content, files in content_map.items():
        if len(files) > 1:
            print(f"  - Identical content in: {files}")

    print("\n[!] KEY COLLISIONS (Logical Overwrites):")
    for target, key_map in collisions.items():
        print(f"  Target: {target}")
        for key, files in key_map.items():
            if len(files) > 1:
                print(f"    - Key '{key}' modified by: {files}")


if __name__ == "__main__":
    main()
