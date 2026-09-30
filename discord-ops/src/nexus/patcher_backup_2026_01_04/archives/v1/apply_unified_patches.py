#!/usr/bin/env python3
"""
DayZ Unified Patch Applicator (Refactored)
Uses PatchEngine for modular, code-driven patching.
"""

import json
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(REPO_ROOT))

# Local imports
from src.mildlyawesome.patcher.engine import PatchEngine
from src.mildlyawesome.patcher.features.goopsta import (
    patch_boost_heli_crashes,
    patch_custom_layout_ezstreet,
    patch_disable_dynamic_gas,
    patch_enable_container_damage,
    patch_lock_containers_event,
    patch_loot_pool_removals,
    patch_no_fog,
    patch_unlimited_stamina,
)
from src.mildlyawesome.patcher.resolver import PatchResolver

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("patch_applicator")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STAGING_DIR = Path(
    os.environ.get(
        "STAGING_DIR",
        REPO_ROOT / "staging" / "ezstreet" / "dayzxb_missions" / "dayzOffline.chernarusplus",
    )
).resolve()
MANIFEST_FILE = REPO_ROOT / "backend/patcher/patches/manifest.json"
PATCHES_DIR = REPO_ROOT / "backend/patcher/patches"
SUMMARY_FILE = REPO_ROOT / "backend/scripts/apply_summary.json"


def check_conflicts(manifest_path, patches_dir):
    """Scan manifesto for conflicting patch targets."""
    log.info("--- CHECKING FOR PATCH CONFLICTS ---")
    if not manifest_path.exists():
        return

    with open(manifest_path) as f:
        data = json.load(f)

    target_history = {}  # TargetFile -> [(PatchFile, Type)]

    for entry in data.get("patches", []):
        if not entry.get("enabled", False):
            continue

        p_file = entry.get("file")
        p_def_path = patches_dir / p_file

        if not p_def_path.exists():
            continue

        try:
            with open(p_def_path) as pf:
                p_data = json.load(pf)

            # Determine Target and Type
            target = None
            ptype = "unknown"

            if "target" in p_data:
                target = p_data["target"]
                ptype = p_data.get("type", "raw_copy")
            elif "target_file" in p_data:
                target = p_data["target_file"]
                ptype = "xml_patch"

            # Heuristics
            if "cfggameplay" in p_file and target is None:
                target = "cfggameplay.json"
                ptype = "json_patch"

            if target:
                if target not in target_history:
                    target_history[target] = []

                # Check Conflict
                history = target_history[target]
                if history:
                    # Logic: If current is 'raw_copy', it OVERWRITES previous patches
                    if ptype == "raw_copy":
                        log.warning(
                            f"CONFLICT WARNING: Patch '{p_file}' (raw_copy) will OVERWRITE previous modifications to '{target}' by {[x[0] for x in history]}"
                        )

                target_history[target].append((p_file, ptype))

        except Exception:
            pass


def run_modular_features(engine: PatchEngine):
    """Executes the code-driven modular patches."""
    log.info("--- RUNNING MODULAR FEATURES (CODE-DRIVEN) ---")
    results = [
        patch_unlimited_stamina(engine),
        patch_enable_container_damage(engine),
        patch_no_fog(engine),
        patch_disable_dynamic_gas(engine),
        patch_boost_heli_crashes(engine),
        patch_lock_containers_event(engine),
        patch_custom_layout_ezstreet(engine),
        patch_loot_pool_removals(engine),
        # patch_lower_misc_clothes_spawn(engine)
    ]
    log.info(f"--- MODULAR FEATURES COMPLETE ({sum(1 for r in results if r)} applied) ---")


def main():
    log.info("=== UNIFIED PATCH APPLICATOR (PYTHON) ===")
    log.info(f"Staging Dir: {STAGING_DIR}")

    engine = PatchEngine(STAGING_DIR, REPO_ROOT)

    # Check Conflicts
    check_conflicts(MANIFEST_FILE, PATCHES_DIR)

    # 1. Process Manifest (Base)
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE) as f:
            manifest = json.load(f)

        raw_patches = manifest.get("patches", [])

        try:
            # RESOLUTION STEP
            resolver = PatchResolver(raw_patches)
            sorted_patches = resolver.resolve()
            enabled_patches = resolver.validate_enabled_chain(sorted_patches)

            log.info(f"--- PROCESSING MANIFEST ({len(enabled_patches)} patches enable) ---")

            for entry in enabled_patches:
                # Avoid re-applying GOOPSTA features if they exist in manifest
                if any(
                    key in entry["file"]
                    for key in [
                        "no_fog",
                        "stamina",
                        "container_damage",
                        "dynamic_gas",
                        "heli_crashes",
                        "locked_containers",
                    ]
                ):
                    continue

                patch_file_path = PATCHES_DIR / entry["file"]
                if not patch_file_path.exists():
                    log.warning(f"[MISSING] {entry['file']}")
                    continue

                try:
                    with open(patch_file_path) as f:
                        patch = json.load(f)

                    ptype = patch.get("type")
                    pid = patch.get("id", entry["file"])

                    if ptype == "script":
                        engine.apply_script_patch(pid, patch.get("script_file"))
                    elif ptype == "raw_copy":
                        engine.apply_raw_copy(pid, patch.get("source"), patch.get("target"))
                    elif ptype == "xml_patch":
                        data_xml = None
                        data_file = patch.get("data_file")
                        if data_file:
                            df_path = PATCHES_DIR / data_file
                            if df_path.exists():
                                with open(df_path) as df:
                                    data_xml = df.read()

                        engine.apply_xml_patch(
                            pid,
                            patch.get("target", "db/types.xml"),
                            patch.get("complex_patches", []),
                            data_xml=data_xml,
                        )
                    else:
                        engine.apply_gameplay_patch(pid, patch.get("path", ""), patch.get("values", {}))
                except Exception as e:
                    log.error(f"Failed manifest patch {entry['file']}: {e}")
        except Exception as e:
            log.error(f"Patch resolution failed: {e}")
            sys.exit(1)
    else:
        log.warning("Manifest not found.")

    # 2. Run Modular Code-Driven Patches (Priority / Overrides)
    run_modular_features(engine)

    log.info("All patches processed successfully.")


if __name__ == "__main__":
    main()
