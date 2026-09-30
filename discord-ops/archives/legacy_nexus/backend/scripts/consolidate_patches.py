import json
import os
import shutil
from pathlib import Path

PATCHES_ROOT = Path("backend/patcher/patches")
MANIFEST_FILE = PATCHES_ROOT / "manifest.json"


def main():
    if not MANIFEST_FILE.exists():
        print("Manifest not found!")
        return

    with open(MANIFEST_FILE) as f:
        manifest = json.load(f)

    # Track moved files to avoid double-moving or overwriting
    # Map: original_abs_path -> new_rel_path_in_patches
    moved_map = {}

    def get_new_name(original_path: Path):
        # Flatten path: tony_128/db/events.xml -> tony_128_db_events.xml
        # But try to keep it simple if unique: events.xml
        # For now, let's use a safe flattening strategy:
        # parent_name + filename (if parent is not patches)

        # parts relative to PATCHES_ROOT
        try:
            rel = original_path.relative_to(PATCHES_ROOT)
        except ValueError:
            # It might be relative path string
            rel = Path(original_path)

        if len(rel.parts) == 1:
            return rel.name  # Already in root

        # Flatten: join parts with underscore, but skip 'custom', 'db' if generic?
        # Actually, let's just use the filename first, check for collision.
        candidate = rel.name
        if (PATCHES_ROOT / candidate).exists() and str(original_path.resolve()) != str(
            (PATCHES_ROOT / candidate).resolve()
        ):
            # Collision! Prepend parent
            candidate = f"{rel.parts[0]}_{rel.name}"

        return candidate

    def move_file(rel_path_str):
        if not rel_path_str:
            return None

        # Handle cases where path is absolute or relative to repo root
        # Typically patches use "backend/patcher/patches/..." or relative.
        # We need to resolve it to a Path object.

        if rel_path_str.startswith("backend/patcher/patches/"):
            clean_rel = rel_path_str.replace("backend/patcher/patches/", "")
            src_path = PATCHES_ROOT / clean_rel
        else:
            src_path = PATCHES_ROOT / rel_path_str

        if not src_path.exists():
            print(f"Warning: Source file missing: {src_path}")
            return rel_path_str

        if src_path.resolve() in moved_map:
            return moved_map[src_path.resolve()]

        new_name = get_new_name(src_path)
        dest_path = PATCHES_ROOT / new_name

        # Check collision again for safety
        counter = 1
        while dest_path.exists() and dest_path.resolve() != src_path.resolve():
            dest_path = PATCHES_ROOT / f"{dest_path.stem}_{counter}{dest_path.suffix}"
            counter += 1

        print(f"Moving {src_path} -> {dest_path}")
        shutil.move(src_path, dest_path)

        moved_map[src_path.resolve()] = dest_path.name
        return dest_path.name

    new_manifest = []

    print("--- Processing Manifest Entries ---")
    for entry in manifest.get("patches", []):
        file_path = entry.get("file")
        new_file_name = move_file(file_path)

        if new_file_name:
            entry["file"] = new_file_name

            # Now open the file and update internal references if it's a JSON
            dest_abs = PATCHES_ROOT / new_file_name
            if dest_abs.suffix == ".json":
                try:
                    with open(dest_abs) as pf:
                        content = json.load(pf)

                    changed = False
                    for key in ["source", "patch_file", "data_file"]:
                        if key in content:
                            old_val = content[key]
                            new_val = move_file(old_val)
                            if new_val:
                                content[key] = new_val  # Update to just filename (relative to patches dir)
                                changed = True

                    if changed:
                        with open(dest_abs, "w") as pf:
                            json.dump(content, pf, indent=4)

                except Exception as e:
                    print(f"Error updating JSON content for {dest_abs}: {e}")

        new_manifest.append(entry)

    # Vacuum: Move remaining files in subdirs
    print("--- Vacuuming Leftovers ---")
    for root, dirs, files in os.walk(PATCHES_ROOT):
        root_path = Path(root)
        if root_path == PATCHES_ROOT:
            continue

        for f in files:
            src = root_path / f
            if src.name == "manifest.json":
                continue
            if src.resolve() not in moved_map:
                move_file(str(src.relative_to(PATCHES_ROOT)))

    # Clean up empty dirs
    for root, dirs, files in os.walk(PATCHES_ROOT, topdown=False):
        for d in dirs:
            dir_path = Path(root) / d
            try:
                dir_path.rmdir()  # Only removes empty
            except:
                pass

    manifest["patches"] = new_manifest
    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=2)

    print("Consolidation Complete.")


if __name__ == "__main__":
    main()
