#!/usr/bin/env python3
"""
DayZ Unified Patch Applicator (Python Port)
Consolidates all numbered patches (01-12) from patcher/patches
and applies them to cfggameplay.json and XML files in staging.
Inspired by apply_patches.js reference.
"""
import os
import sys
import json
import math
import logging
from pathlib import Path
from typing import Dict, Any, List

# Ensure lxml is available
try:
    from lxml import etree
except ImportError:
    print("Error: lxml is required. Run 'pip install lxml'")
    sys.exit(1)

import jsonpatch

sys.path.append(str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("patch_applicator")

PATCHES_DIR = Path("/home/toxic/dayz_workspace/dayz_discord_ops_repo/patcher/patches")
STAGING_DIR = Path("/home/toxic/dayz_workspace/dayz_discord_ops_repo/backend_data/staging/dayzxb_missions/dayzOffline.chernarusplus")
REPO_ROOT = Path("/home/toxic/dayz_workspace/dayz_discord_ops_repo")
MANIFEST_FILE = PATCHES_DIR / "manifest.json"

def load_manifest() -> dict:
    """Load the patch manifest."""
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE, 'r') as f:
            return json.load(f)
    return {"patches": [], "order": []}

def deep_merge(target: Dict, source: Dict):
    """Deep merge source dict into target dict."""
    for key, value in source.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            deep_merge(target[key], value)
        else:
            target[key] = value
    return target

def apply_gameplay_patch(patch: Dict, filename: str) -> bool:
    """Apply JSON patch to cfggameplay.json"""
    if "path" not in patch:
        log.error(f"[ERROR] JSON patch {filename} is missing 'path'.")
        return False

    target_file = STAGING_DIR / "cfggameplay.json"
    if not target_file.exists():
        log.error(f"Target file not found: {target_file}")
        return False

    try:
        with open(target_file, 'r') as f:
            config = json.load(f)
        
        # Navigate path
        path_parts = patch["path"].split('.')
        target = config
        
        # Create intermediate keys if missing
        for i, part in enumerate(path_parts[:-1]):
            if part not in target:
                target[part] = {}
            target = target[part]
        
        last_key = path_parts[-1]
        if last_key not in target:
            target[last_key] = {}
        
        # Apply values
        deep_merge(target[last_key], patch["values"])
        
        with open(target_file, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    
    except Exception as e:
        log.error(f"Failed to apply gameplay patch {filename}: {e}")
        return False

def apply_xml_patch(patch: Dict, patch_file_path: Path) -> bool:
    """Apply XML patch (types, events, etc)"""
    target_file = STAGING_DIR / patch["target"] if "target" in patch else STAGING_DIR / "db/types.xml" # Default target? 
    # Use target from patch if available, else infer? 
    # The reference JS implies patch.target exists for XML patches.
    # Looking at unlimted_stamina.json it has "target": "cfggameplay.json"
    # Looking at manifest, it doesn't specify target file for the entry.
    
    # We need to peek at the patch file to see if it has "target"
    if "target" in patch:
        target_file = STAGING_DIR / patch["target"]
    else:
        # Fallback based on content?
        # But wait, the JS reference says: if (patch.type === 'xml_patch' || patch.target.endsWith('.xml'))
        pass

    if not target_file.exists():
        log.warning(f"[DEBUG] Cannot find target file: {target_file}")
        return False
    
    try:
        parser = etree.XMLParser(remove_blank_text=False)
        tree = etree.parse(str(target_file), parser)
        modified = False
        
        # Unified task list
        tasks = patch.get("complex_patches", [])
        if "xpath" in patch and "values" in patch:
            tasks.append({"xpath": patch["xpath"], "values": patch["values"]})
            
        # Handle Namespace issues by removing them or using local-name() if needed
        # DayZ XML usually doesn't strictly follow namespaces, but lxml is strict.
        
        # Handle XPath Attribute Updates
        for task in tasks:
            nodes = tree.xpath(task["xpath"])
            for node in nodes:
                for attr, val in task["values"].items():
                    if "_multiplier" in attr:
                        base_attr = attr.replace("_multiplier", "")
                        current = float(node.get(base_attr, "0"))
                        node.set(base_attr, str(current * float(val)))
                    else:
                        node.set(attr, str(val))
                    modified = True
                    
        # Handle Item Lists with Multipliers (Vehicle counts in types.xml)
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
                            
        # Handle Raw XML block injection
        data_file = patch_file_path.with_name(patch_file_path.stem + "_data.xml")
        if data_file.exists():
            data_tree = etree.parse(str(data_file), parser)
            new_types = data_tree.findall("type")
            root = tree.getroot()
            
            for new_type in new_types:
                type_name = new_type.get("name")
                existing = tree.xpath(f"//type[@name='{type_name}']")
                if existing:
                    # Replace
                    parent = existing[0].getparent()
                    parent.replace(existing[0], new_type)
                else:
                    # Append
                    root.append(new_type)
                modified = True

        if modified:
            tree.write(str(target_file), pretty_print=True, xml_declaration=True, encoding="utf-8")
        return modified

    except Exception as e:
        log.error(f"Failed to apply XML patch {patch_file_path.name}: {e}")
        return False


def apply_raw_copy(patch: Dict) -> bool:
    """
    Copy a file from repository into staging without transformation.
    Patch schema:
      type: "raw_copy"
      source: "server/ezstreet/Loot_Presets_Library.json"
      target: "custom/Loot_Presets_Library.json"
    """
    source_rel = patch.get("source")
    target_rel = patch.get("target")
    if not source_rel or not target_rel:
        log.error("[ERROR] raw_copy patch missing source/target")
        return False


def apply_generate_presets(patch: Dict) -> bool:
    """
    Generate Loot_Presets_Library.json dynamically from an EZStreet_Containers.json-like source.

    Patch schema:
      type: "generate_presets"
      source: "server/ezstreet/EZStreet_Containers.json"
      target: "custom/Loot_Presets_Library.json"
      radius: 50  (optional, meters for cluster assignment)
    """
    source_rel = patch.get("source")
    target_rel = patch.get("target")
    radius = float(patch.get("radius", 50.0))

    if not source_rel or not target_rel:
        log.error("[ERROR] generate_presets patch missing source/target")
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
        if not anchors:
            log.error("[ERROR] generate_presets found no anchors containing 'ContainerLocked'")
            return False

        clusters = [{"anchor": a, "items": [a]} for a in anchors]

        def dist(a, b):
            ax, ay, az = a["pos"]
            bx, by, bz = b["pos"]
            return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)

        for obj in objects:
            if obj in anchors:
                continue
            nearest_idx = None
            nearest_dist = 1e9
            for i, c in enumerate(clusters):
                d = dist(obj, c["anchor"])
                if d < nearest_dist:
                    nearest_dist = d
                    nearest_idx = i
            if nearest_dist <= radius and nearest_idx is not None:
                clusters[nearest_idx]["items"].append(obj)

        library = []
        for idx, c in enumerate(clusters, start=1):
            anchor = c["anchor"]
            ax, ay, az = anchor["pos"]
            normalized = []
            for o in c["items"]:
                ox, oy, oz = o["pos"]
                normalized.append({
                    "name": o["name"],
                    "relPos": [ox - ax, oy - ay, oz - az],
                    "ypr": o.get("ypr", [0, 0, 0]),
                    "scale": o.get("scale", 1.0),
                    "enableCEPersistency": o.get("enableCEPersistency", 0),
                    "customString": o.get("customString", "")
                })
            library.append({
                "id": f"Preset_{idx}_{anchor['name']}",
                "containerType": anchor["name"],
                "itemCount": len(normalized),
                "originalPos": anchor["pos"],
                "objects": normalized
            })

        with open(target, "w") as f:
            json.dump(library, f, indent=4)
        log.info(f"[OK] generate_presets wrote {len(library)} presets to {target_rel}")
        return True
    except Exception as e:
        log.error(f"[FAIL] generate_presets {source_rel}: {e}")
        return False

    source = (REPO_ROOT / source_rel).resolve()
    target = (STAGING_DIR / target_rel).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    if not source.exists():
        log.error(f"[ERROR] raw_copy source missing: {source}")
        return False

    try:
        import shutil

        shutil.copy2(source, target)
        log.info(f"[OK] raw_copy {source_rel} -> {target_rel}")
        return True
    except Exception as e:
        log.error(f"[FAIL] raw_copy {source_rel}: {e}")
        return False

def main():
    log.info("=== UNIFIED PATCH APPLICATOR (PYTHON) ===")
    log.info(f"Staging Dir: {STAGING_DIR}")
    
    if not MANIFEST_FILE.exists():
        log.error("Manifest not found!")
        return

    try:
        with open(MANIFEST_FILE, 'r') as f:
            manifest = json.load(f)
    except Exception as e:
        log.error(f"Failed to load manifest: {e}")
        return

    applied_count = 0
    skipped_count = 0

    for entry in manifest.get("patches", []):
        if not entry.get("enabled", False):
            log.info(f"[DISABLED] {entry['file']}")
            skipped_count += 1
            continue
            
        patch_file_path = PATCHES_DIR / entry["file"]
        if not patch_file_path.exists():
            log.warning(f"[MISSING]  {entry['file']}")
            skipped_count += 1
            continue

        try:
            with open(patch_file_path, 'r') as f:
                patch = json.load(f)
            
            success = False
            ptype = patch.get("type")

            if ptype == "raw_copy":
                success = apply_raw_copy(patch)
            elif ptype == "generate_presets":
                success = apply_generate_presets(patch)
            elif ptype == "xml_patch" or patch.get("target", "").endswith(".xml"):
                success = apply_xml_patch(patch, patch_file_path)
            else:
                # Default to gameplay/json patch if target isn't XML
                success = apply_gameplay_patch(patch, entry["file"])
            
            if success:
                log.info(f"[OK]       {entry['file']}")
                applied_count += 1
            else:
                log.info(f"[SKIP]     {entry['file']}")
                skipped_count += 1
                
        except Exception as e:
            log.error(f"[FAIL]     {entry['file']}: {e}")
            skipped_count += 1

    log.info("---")
    log.info(f"Results: {applied_count} applied, {skipped_count} skipped.")

if __name__ == "__main__":
    main()
