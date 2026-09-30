import json
import logging
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("deploy_packer")

from src.mildlyawesome.config import get_settings
settings = get_settings()

REPO_ROOT = settings.chronos_root
PATCH_DIR = REPO_ROOT / "backend/patcher/patches"
BASELINE_DIR = REPO_ROOT / "staging/baselines/dz_128/dayzOffline.chernarusplus"
OUTPUT_DIR = REPO_ROOT / "staging/deploy_pack_v1"

# Target Wishlist Patches (5 Atomic Patches)
PATCHES = [
    "gameplay/no_base_damage.json",
    "gameplay/build_anywhere.json",
    "gameplay/no_weather.json",
    "atomic/boost_heli_crashes.json",
    "economy/pristine_loot.json",
]


def load_json(path):
    with open(path) as f:
        return json.load(f)


def apply_json_patch(baseline_file, patch_data, output_file):
    """Apply JSON patch to baseline (Cumulative)"""
    # Load from Output if exists (Cumulative), else Baseline
    source_path = output_file if output_file.exists() else baseline_file

    if source_path.exists():
        with open(source_path) as f:
            data = json.load(f)
    else:
        log.warning(f"Source JSON missing: {source_path}")
        data = {}

    # Patch Logic
    path_key = patch_data.get("path")  # e.g. "GeneralData" or "BaseBuildingData.HologramData"
    values = patch_data.get("values", {})

    target_obj = data

    if path_key:
        # Traverse Dot Notation
        keys = path_key.split(".")

        # Navigate to the parent of the last key
        for k in keys:
            if k not in target_obj:
                target_obj[k] = {}
            target_obj = target_obj[k]

        # target_obj is now the dictionary at the path
        if isinstance(target_obj, dict):
            target_obj.update(values)
        else:
            # Should not happen if structure is valid
            log.warning(f"Target path {path_key} is not a dict, cannot update")
    else:
        # Root update
        data.update(values)

    # Write Output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(data, f, indent=4)
    log.info(f"Patched JSON: {output_file.name}")


def apply_xml_patch(baseline_file, patch_data, output_file):
    """Apply XML patch (Cumulative, Child Elements)"""
    source_path = output_file if output_file.exists() else baseline_file

    if not source_path.exists():
        log.error(f"Source XML missing: {source_path}")
        return

    tree = ET.parse(source_path)
    root = tree.getroot()

    complex_patches = patch_data.get("complex_patches", [])

    for instruction in complex_patches:
        xpath = instruction.get("xpath")  # e.g. //event[@name='StaticHeliCrash']
        values = instruction.get("values", {})

        # XPath Matching
        if xpath.startswith("//"):
            tag_part = xpath[2:].split("[")[0]
            filter_attr, filter_val = None, None

            if "[" in xpath:
                condition = xpath.split("[")[1].strip("]")
                if condition.startswith("@"):
                    if "=" in condition:
                        parts = condition.split("=")
                        filter_attr = parts[0].strip("@")
                        filter_val = parts[1].strip("'\"")

            # Iterate and patch
            for elem in root.iter(tag_part):
                match = False
                if filter_attr:
                    if elem.get(filter_attr) == filter_val:
                        match = True
                else:
                    match = True

                if match:
                    # Update Children or Attributes
                    for k, v in values.items():
                        # check if child exists
                        child = elem.find(k)
                        if child is not None:
                            child.text = str(v)
                        else:
                            # If not a child, assumed attribute?
                            # But DayZ usually uses children for values like nominal, min, max.
                            # If it doesn't exist, create it?
                            # For safety, let's create it.
                            new_child = ET.SubElement(elem, k)
                            new_child.text = str(v)

    # Write Output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_file, encoding="UTF-8", xml_declaration=True)
    log.info(f"Patched XML: {output_file.name}")


def main():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    # Create structure
    (OUTPUT_DIR / "mission").mkdir(parents=True)

    manifest = {"version": "1.0.1", "patches_active": [], "generated_at": "2026-01-02", "files": []}

    processed_files = set()

    for patch_rel in PATCHES:
        patch_path = PATCH_DIR / patch_rel
        if not patch_path.exists():
            log.error(f"Patch missing: {patch_path}")
            continue

        try:
            patch = load_json(patch_path)

            # Determine target
            target_rel = patch.get("target") or patch.get("file")

            baseline_file = BASELINE_DIR / target_rel
            output_file = OUTPUT_DIR / "mission" / target_rel

            # Apply Patch (Logic now handles cumulative read from output_file)
            if str(target_rel).endswith(".json"):
                apply_json_patch(baseline_file, patch, output_file)
            elif str(target_rel).endswith(".xml"):
                apply_xml_patch(baseline_file, patch, output_file)
            else:
                log.warning(f"Unknown file type for {target_rel}")
                continue

            manifest["patches_active"].append(patch.get("id", patch_rel))
            manifest["files"].append(str(target_rel))
            processed_files.add(target_rel)

        except Exception:
            log.exception(f"Failed to apply {patch_rel}")

    # Copy files that were modified to 'processed' list??
    # Actually, we might want to copy unmodified files too if this is a full mission pack.
    # But for a patch pack, only modified files are usually delivered.
    # User constraint: "FTP-safe operations".
    # Delivering ONLY modified files is safer/smaller.

    with open(OUTPUT_DIR / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"DEPLOY PACK READY: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
