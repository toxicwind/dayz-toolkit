import json
import logging
from collections import defaultdict
from pathlib import Path

PATCHES_DIR = Path("backend/patcher/patches")
MANIFEST_FILE = PATCHES_DIR / "manifest.json"

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("audit")


def load_json(path):
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}


def main():
    if not MANIFEST_FILE.exists():
        log.error("Manifest missing")
        return

    manifest = load_json(MANIFEST_FILE)
    patches = manifest.get("patches", [])

    # Map: TargetFile -> List of (PatchFile, ModificationType, PatchID)
    file_impact_map = defaultdict(list)

    print(f"--- Auditing {len(patches)} Patches ---")

    for entry in patches:
        if not entry.get("enabled", False):
            continue

        p_file = entry.get("file")
        p_path = PATCHES_DIR / p_file

        if not p_path.exists():
            log.warning(f"MISSING FILE: {p_file}")
            continue

        # Determine Target
        # Most patches are JSON definitions that specify "target" or "data_file" or "patch_file"
        # Some legacy patches might be weird.

        definition = load_json(p_path)

        target = "UNKNOWN"
        mod_type = "UNKNOWN"

        # Raw Copy
        if "target" in definition:
            target = definition["target"]
            mod_type = definition.get("type", "raw_copy")

        # Regex/XML Patch often implied by filename or internal logic?
        # Let's see how apply_unified_patches detects target.
        # It relies on specific keys or logic.
        elif "target_file" in definition:
            target = definition["target_file"]
            mod_type = "xml_patch"  # or regex
        elif "files" in definition:  # Multi-file targets?
            # Some JSON patches target specific sections of cfggameplay.
            pass
        else:
            # Heuristic based on filename or contents
            # e.g. "db/events.xml.patch" targets "db/events.xml"
            # But the JSON WRAPPER "events.xml.patch" (if it is a wrapper) points to a data file?
            # Actually Step 1779 moved raw files too.
            # Let's inspect content.
            pass

        # Normalize Target
        # Many patches update cfggameplay.json via implicit logic (mod_type "json_merge"?)
        if "cfggameplay" in p_file:
            target = "cfggameplay.json"
            mod_type = "json_merge"

        if "events.xml" in p_file or "events.json" in p_file:
            if target == "UNKNOWN":
                target = "db/events.xml"
            if mod_type == "UNKNOWN":
                mod_type = "xml_merge"

        if "types.xml" in p_file:
            target = "db/types.xml"

        if "globals.xml" in p_file:
            target = "db/globals.xml"

        file_impact_map[target].append((p_file, mod_type, entry.get("description", "")))

    print("\n--- CONFLICT REPORT ---")
    for target, entries in file_impact_map.items():
        if len(entries) > 1:
            print(f"\n[TARGET] {target}")
            # Check for Critical Conflicts (Multiple Raw Copies)
            raw_copies = [x for x in entries if "raw_copy" in x[1]]
            if len(raw_copies) > 1:
                print(f"  !! CRITICAL: Multiple Raw Copies ({len(raw_copies)}) - Last one wins!")

            for fname, mtype, desc in entries:
                print(f"  - {fname} ({mtype}) : {desc}")


if __name__ == "__main__":
    main()
