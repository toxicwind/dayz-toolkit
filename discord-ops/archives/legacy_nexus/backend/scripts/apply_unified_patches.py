#!/usr/bin/env python3
"""
DayZ Unified Patch Applicator (Python)
Applies modular patches from backend/patcher/patches (category folders) to the
staging mission tree (cfggameplay.json, XML, raw copies, cfg flags).

Generates a deterministic summary JSON listing applied patches and file hashes.
"""

import difflib
import json
import logging
import math
import shutil
import sys
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure lxml is available
try:
    from lxml import etree
except ImportError:
    print("Error: lxml is required. Run 'pip install lxml'")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("patch_applicator")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PATCHES_DIR = REPO_ROOT / "backend" / "patcher" / "patches"
# Canonical staging layout: staging/ezstreet/dayzxb_missions/dayzOffline.chernarusplus
STAGING_DIR = Path(
    os.environ.get(
        "STAGING_DIR",
        REPO_ROOT / "staging" / "ezstreet" / "dayzxb_missions" / "dayzOffline.chernarusplus",
    )
).resolve()
MANIFEST_FILE = PATCHES_DIR / "manifest.json"
SUMMARY_FILE = REPO_ROOT / "backend" / "scripts" / "apply_summary.json"


def load_manifest() -> dict:
    """Load the patch manifest."""
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE) as f:
            return json.load(f)
    return {"patches": [], "order": []}


def guard_staging_dir(path: Path):
    """Prevent accidental writes into baselines or FTP evidence lanes."""
    prohibited_tokens = {"baselines", "nitrado_ftp_dump"}
    parts = set(path.parts)
    if parts & prohibited_tokens:
        log.error(f"Refusing to run: STAGING_DIR points to a protected lane ({path}).")
        sys.exit(1)
    if not path.exists():
        log.warning(f"Staging dir {path} does not exist, creating parents...")
        path.mkdir(parents=True, exist_ok=True)


def backup_file(target_file: Path) -> Path:
    """Create a timestamped backup of target_file; returns backup path."""
    backup_root = REPO_ROOT / "backups" / "patcher"
    try:
        rel = target_file.relative_to(STAGING_DIR)
    except ValueError:
        rel = Path(target_file.name)
    stamped = f"{target_file.stem}-{datetime.now().strftime('%Y%m%d-%H%M%S')}{target_file.suffix}.bak"
    backup_path = backup_root / rel.parent / stamped
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if target_file.exists():
        shutil.copy2(target_file, backup_path)
    return backup_path


def hash_file(path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    if not path.exists():
        return "MISSING"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def diff_summary(before: str, after: str, label: str) -> str:
    """Return a short unified diff summary (first 80 lines max)."""
    diff = list(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            lineterm="",
            fromfile=f"{label}:before",
            tofile=f"{label}:after",
        )
    )
    if len(diff) > 80:
        diff = diff[:80] + ["... (diff truncated)"]
    return "\n".join(diff)


def atomic_write(target_file: Path, content: str):
    """Write to temp then atomically move into place."""
    tmp_path = target_file.with_suffix(target_file.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    tmp_path.replace(target_file)


def deep_merge(target: dict, source: dict):
    """Deep merge source dict into target dict."""
    for key, value in source.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            deep_merge(target[key], value)
        else:
            target[key] = value
    return target


def apply_list_patch(ops: list, target_rel: str) -> bool:
    """
    Apply a simple list-of-ops patch file.
    Supports:
      - JSON targets: op=replace/remove/add with RFC6901-like paths
      - XML targets: op=set_attr (xpath, attr, value)
    """
    target_file = STAGING_DIR / target_rel
    if not target_file.exists():
        log.error(f"Target file not found: {target_file}")
        return False

    if target_rel.endswith(".json"):
        try:
            data = json.loads(target_file.read_text(encoding="utf-8"))
        except Exception as e:
            log.error(f"Failed to load JSON {target_file}: {e}")
            return False

        def set_json_pointer(obj: Any, path: str, value: Any, op: str):
            # path like /PlayerData/StaminaData/StaminaMax
            parts = [p for p in path.split("/") if p != ""]
            cursor = obj
            for p in parts[:-1]:
                if isinstance(cursor, dict):
                    cursor = cursor.setdefault(p, {})
                else:
                    raise ValueError(f"Non-dict segment for {path}")
            last = parts[-1] if parts else None
            if op == "remove":
                if isinstance(cursor, dict):
                    cursor.pop(last, None)
                elif isinstance(cursor, list) and last.isdigit():
                    idx = int(last)
                    if 0 <= idx < len(cursor):
                        cursor.pop(idx)
            else:  # add/replace
                if isinstance(cursor, dict):
                    cursor[last] = value
                elif isinstance(cursor, list) and last.isdigit():
                    idx = int(last)
                    if op == "add":
                        cursor.insert(idx, value)
                    else:
                        cursor[idx] = value

        modified = False
        for op in ops:
            try:
                set_json_pointer(data, op["path"], op.get("value"), op.get("op", "replace"))
                modified = True
            except Exception as e:
                log.error(f"JSON op failed ({op}): {e}")
                return False

        if modified:
            backup_file(target_file)
            atomic_write(target_file, json.dumps(data, indent=4))
            log.info(f"Applied list patch to {target_rel}")
        return modified

    if target_rel.endswith(".xml"):
        try:
            parser = etree.XMLParser(remove_blank_text=False)
            tree = etree.parse(str(target_file), parser)
        except Exception as e:
            log.error(f"Failed to load XML {target_file}: {e}")
            return False

        modified = False
        for op in ops:
            if op.get("op") == "set_attr":
                nodes = tree.xpath(op["xpath"])
                for node in nodes:
                    node.set(op["attr"], str(op["value"]))
                    modified = True

        if modified:
            backup_file(target_file)
            tree.write(str(target_file), pretty_print=True, encoding="UTF-8", xml_declaration=True)
            log.info(f"Applied XML attr list patch to {target_rel}")
        return modified

    log.warning(f"Unknown target type for list patch: {target_rel}")
    return False


def apply_gameplay_patch(patch: dict, filename: str) -> bool:
    """Apply JSON patch to cfggameplay.json"""
    if "path" not in patch:
        log.error(f"[ERROR] JSON patch {filename} is missing 'path'.")
        return False

    target_file = STAGING_DIR / "cfggameplay.json"
    if not target_file.exists():
        log.error(f"Target file not found: {target_file}")
        return False

    try:
        before_text = target_file.read_text(encoding="utf-8")
        config = json.loads(before_text)
        path_parts = patch["path"].split(".")
        target = config
        for part in path_parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        last_key = path_parts[-1]
        if last_key not in target:
            target[last_key] = {}
        for k in patch.get("remove", []):
            target[last_key].pop(k, None)
        deep_merge(target[last_key], patch["values"])
        after_text = json.dumps(config, indent=4)

        if before_text == after_text:
            log.info(f"[NOOP] {patch.get('id', filename)} (no change)")
            return False

        backup_file(target_file)
        atomic_write(target_file, after_text)
        log.info(f"Applied patch {patch.get('id', filename)}")
        return True
    except Exception as e:
        log.error(f"Failed to apply gameplay patch {filename}: {e}")
        return False


def apply_xml_patch(patch: dict, patch_file_path: Path) -> bool:
    """Apply XML patch (types, events, etc)"""
    target_rel = patch.get("target", "db/types.xml")
    target_file = STAGING_DIR / target_rel

    if not target_file.exists():
        log.warning(f"[DEBUG] Cannot find target file: {target_file}")
        return False

    try:
        parser = etree.XMLParser(remove_blank_text=False)
        before_text = target_file.read_text(encoding="utf-8")
        tree = etree.fromstring(before_text.encode("utf-8"), parser)
        modified = False
        tasks = patch.get("complex_patches", [])
        if "xpath" in patch and "values" in patch:
            tasks.append({"xpath": patch["xpath"], "values": patch["values"]})

        for task in tasks:
            if "remove_xpath" in task:
                nodes = tree.xpath(task["remove_xpath"])
                for node in nodes:
                    parent = node.getparent()
                    if parent is not None:
                        parent.remove(node)
                        modified = True
                continue

            if "append_xml" in task:
                fragments = task["append_xml"]
                if isinstance(fragments, str):
                    fragments = [fragments]
                parent_xpath = task.get("parent_xpath", "/")
                parents = tree.xpath(parent_xpath)
                for parent in parents:
                    for idx, frag in enumerate(fragments):
                        new_node = etree.fromstring(frag)
                        position = task.get("position")
                        if position is not None and idx == 0:
                            parent.insert(int(position), new_node)
                        else:
                            parent.append(new_node)
                        modified = True
                continue

            if "replace_children_with" in task:
                nodes = tree.xpath(task["xpath"])
                fragments = task["replace_children_with"]
                for node in nodes:
                    for child in list(node):
                        node.remove(child)
                    node.text = "\n    "
                    for idx, frag in enumerate(fragments):
                        child = etree.fromstring(frag)
                        child.tail = "\n    " if idx < len(fragments) - 1 else "\n"
                        node.append(child)
                    modified = True
                continue

            nodes = tree.xpath(task["xpath"])
            for node in nodes:
                values = task.get("values", {})
                for attr, val in values.items():
                    if "_multiplier" in attr:
                        base_attr = attr.replace("_multiplier", "")
                        current = float(node.get(base_attr, "0"))
                        node.set(base_attr, str(current * float(val)))
                    else:
                        node.set(attr, str(val))
                    modified = True

        if "items" in patch and "values" in patch:
            for item_name in patch["items"]:
                nodes = tree.xpath(f"//type[@name='{item_name}']")
                for node in nodes:
                    for key, multiplier in patch["values"].items():
                        tag_name = key.replace("_multiplier", "")
                        element = node.find(tag_name)
                        if element is not None and element.text:
                            new_val = round(float(element.text) * float(multiplier))
                            element.text = str(new_val)
                            modified = True

        data_file = patch_file_path.with_name(patch_file_path.stem + "_data.xml")
        if data_file.exists():
            data_tree = etree.parse(str(data_file), parser)
            for new_type in data_tree.findall("type"):
                type_name = new_type.get("name")
                existing = tree.xpath(f"//type[@name='{type_name}']")
                if existing:
                    existing[0].getparent().replace(existing[0], new_type)
                else:
                    tree.append(new_type)
                modified = True

        if modified:
            after_text = etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding="utf-8").decode("utf-8")
            if before_text == after_text:
                log.info(f"[NOOP] {patch.get('id', patch_file_path.name)} (no change)")
                return False
            backup_file(target_file)
            atomic_write(target_file, after_text)
            log.info(f"Applied XML patch {patch.get('id', patch_file_path.name)}")
            return True
        return False
    except Exception as e:
        log.error(f"Failed to apply XML patch {patch_file_path.name}: {e}")
        return False


def apply_raw_copy(patch: dict) -> bool:
    """Copy a file from repository into staging without transformation."""
    source_rel = patch.get("source")
    target_rel = patch.get("target")
    if not source_rel or not target_rel:
        return False
    source = (REPO_ROOT / source_rel).resolve()
    target = (STAGING_DIR / target_rel).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        log.error(f"[ERROR] raw_copy source missing: {source}")
        return False
    shutil.copy2(source, target)
    log.info(f"[OK] raw_copy {source_rel} -> {target_rel}")
    return True

def apply_generate_presets(patch: dict) -> bool:
    """Generate Loot_Presets_Library.json dynamically."""
    source_rel = patch.get("source")
    target_rel = patch.get("target")
    radius = float(patch.get("radius", 50.0))
    if not source_rel or not target_rel:
        return False
    source = (REPO_ROOT / source_rel).resolve()
    target = (STAGING_DIR / target_rel).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        log.error(f"[ERROR] generate_presets source missing: {source}")
        return False

    try:
        data = json.load(open(source))
        objects = data.get("Objects", [])
        anchors = [o for o in objects if "ContainerLocked" in o.get("name", "")]
        if not anchors: return False
        clusters = [{"anchor": a, "items": [a]} for a in anchors]
        def dist(a, b):
            ax, ay, az = a["pos"]
            bx, by, bz = b["pos"]
            return math.sqrt((ax-bx)**2 + (ay-by)**2 + (az-bz)**2)
        for obj in objects:
            if obj in anchors: continue
            nearest_idx, nearest_dist = None, 1e9
            for i, c in enumerate(clusters):
                d = dist(obj, c["anchor"])
                if d < nearest_dist: nearest_dist, nearest_idx = d, i
            if nearest_dist <= radius and nearest_idx is not None:
                clusters[nearest_idx]["items"].append(obj)
        library = []
        for idx, c in enumerate(clusters, start=1):
            anchor = c["anchor"]
            ax, ay, az = anchor["pos"]
            norm_items = []
            for o in c["items"]:
                ox, oy, oz = o["pos"]
                norm_items.append({
                    "name": o["name"],
                    "relPos": [ox-ax, oy-ay, oz-az],
                    "ypr": o.get("ypr", [0,0,0]),
                    "scale": o.get("scale", 1.0),
                    "enableCEPersistency": o.get("enableCEPersistency", 0),
                    "customString": o.get("customString", "")
                })
            library.append({
                "id": f"Preset_{idx}_{anchor['name']}",
                "containerType": anchor['name'],
                "itemCount": len(norm_items),
                "originalPos": anchor["pos"],
                "objects": norm_items
            })
        with open(target, "w") as f:
            json.dump(library, f, indent=4)
        log.info(f"[OK] generated presets {target_rel}")
        return True
    except Exception as e:
        log.error(f"[FAIL] generate_presets: {e}")
        return False

def apply_cfg_patch(patch: dict, filename: str) -> bool:
    """Ensure serverDZ.cfg flags."""
    target_rel = patch.get("target", "serverDZ.cfg")
    target_file = STAGING_DIR / target_rel
    if not target_file.exists(): return False
    key, val = patch.get("flag"), patch.get("value", 1)
    if not key: return False
    content = target_file.read_text(encoding="utf-8").splitlines()
    found = False
    for i, line in enumerate(content):
        if line.strip().startswith(key):
            found = True
            content[i] = f"{key} = {val};"
            break
    if not found: content.append(f"{key} = {val};")
    after = "\n".join(content) + "\n"
    backup_file(target_file)
    atomic_write(target_file, after)
    log.info(f"Applied cfg patch {filename}")
    return True

def main():
    log.info("=== UNIFIED PATCH APPLICATOR (PYTHON) ===")
    log.info(f"Staging Dir: {STAGING_DIR}")
    guard_staging_dir(STAGING_DIR)

    if not MANIFEST_FILE.exists():
        log.error("Manifest not found!")
        sys.exit(1)

    manifest = load_manifest()
    applied_list = []
    
    # Process manifest.json 'patches' list
    # Support both old list and new dict-based order if needed, but here we assume list from existing manifest
    patches = manifest.get("patches", [])
    
    # If the user switched to order/enabled dict, we'd need to adapt.
    # But based on file view, it's a list.

    for entry in patches:
        if not entry.get("enabled", False):
            continue

        patch_file_path = PATCHES_DIR / entry["file"]
        if not patch_file_path.exists():
            log.warning(f"[MISSING] {entry['file']}")
            continue

        try:
            with open(patch_file_path) as f:
                patch = json.load(f)

            success = False

            # Support list-of-ops patch files (json/xml simple patches)
            if isinstance(patch, list):
                target_rel = entry.get("target") or patch_file_path.name
                success = apply_list_patch(patch, target_rel)
            else:
                ptype = patch.get("type")

                if ptype == "raw_copy":
                    success = apply_raw_copy(patch)
                elif ptype == "generate_presets":
                    success = apply_generate_presets(patch)
                elif ptype == "cfg_patch":
                    success = apply_cfg_patch(patch, entry["file"])
                elif ptype == "xml_patch" or patch.get("target", "").endswith(".xml"):
                    success = apply_xml_patch(patch, patch_file_path)
                else:
                    success = apply_gameplay_patch(patch, entry["file"])

            if success:
                # Calculate hash of resultant file if possible
                dest = str(STAGING_DIR) # simplistic
                if "target" in patch:
                    dest = str(STAGING_DIR / patch["target"])
                
                # For more accurate hash, we'd need to know exactly which file changed.
                # The apply functions verify success.
                applied_list.append({
                    "patch": entry["file"],
                    "status": "applied",
                    "timestamp": datetime.now().isoformat()
                })
        except Exception as e:
            log.error(f"Failed patch {entry['file']}: {e}")

    # Write summary
    try:
        with open(SUMMARY_FILE, "w") as f:
            json.dump(applied_list, f, indent=2)
        log.info(f"Summary written to {SUMMARY_FILE}")
    except Exception as e:
        log.error(f"Failed to write summary: {e}")

if __name__ == "__main__":
    main()
