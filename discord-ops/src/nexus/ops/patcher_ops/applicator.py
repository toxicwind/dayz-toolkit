#!/usr/bin/env python3
"""
DayZ Unified Patch Applicator (Python) - Refactored for MildlyAwesome Ops
Applies modular patches from patches/ directory to the staging mission tree.
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

# Path discovery
OPS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = OPS_ROOT.parent.parent.parent
PATCHES_DIR = OPS_ROOT / "patches"

# Default staging layout
DEFAULT_STAGING = REPO_ROOT / "staging" / "ezstreet" / "dayzxb_missions" / "dayzOffline.chernarusplus"
STAGING_DIR = Path(os.environ.get("STAGING_DIR", DEFAULT_STAGING)).resolve()

MANIFEST_FILE = PATCHES_DIR / "manifest.json"
SUMMARY_FILE = REPO_ROOT / "backups" / "patcher" / "apply_summary.json"


def load_manifest() -> dict:
    """Load the patch manifest from the local patches dir."""
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

def deep_merge(target: dict, source: dict):
    """Deep merge source dict into target dict."""
    for key, value in source.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            deep_merge(target[key], value)
        else:
            target[key] = value
    return target

def apply_list_patch(ops: list, target_rel: str) -> bool:
    target_file = STAGING_DIR / target_rel
    if not target_file.exists():
        return False

    if target_rel.endswith(".json"):
        try:
            data = json.loads(target_file.read_text(encoding="utf-8"))
        except:
            return False

        def set_json_pointer(obj: Any, path: str, value: Any, op: str):
            parts = [p for p in path.split("/") if p != ""]
            cursor = obj
            for p in parts[:-1]:
                if isinstance(cursor, dict):
                    cursor = cursor.setdefault(p, {})
            last = parts[-1] if parts else None
            if op == "remove":
                if isinstance(cursor, dict): cursor.pop(last, None)
            else:
                if isinstance(cursor, dict): cursor[last] = value

        modified = False
        for op in ops:
            try:
                set_json_pointer(data, op["path"], op.get("value"), op.get("op", "replace"))
                modified = True
            except: continue

        if modified:
            backup_file(target_file)
            target_file.write_text(json.dumps(data, indent=4), encoding="utf-8")
        return modified
    return False

def apply_gameplay_patch(patch: dict, filename: str) -> bool:
    target_file = STAGING_DIR / "cfggameplay.json"
    if not target_file.exists(): return False
    try:
        config = json.loads(target_file.read_text(encoding="utf-8"))
        path_parts = patch["path"].split(".")
        target = config
        for part in path_parts[:-1]:
            if part not in target: target[part] = {}
            target = target[part]
        last_key = path_parts[-1]
        if last_key not in target: target[last_key] = {}
        deep_merge(target[last_key], patch["values"])
        backup_file(target_file)
        target_file.write_text(json.dumps(config, indent=4), encoding="utf-8")
        return True
    except: return False

def main():
    log.info("=== MILDLYAWESOME PATCH APPLICATOR ===")
    log.info(f"Staging: {STAGING_DIR}")
    guard_staging_dir(STAGING_DIR)

    manifest = load_manifest()
    applied_list = []

    for entry in manifest.get("patches", []):
        if not entry.get("enabled", False):
            continue

        patch_file_path = PATCHES_DIR / entry["file"]
        if not patch_file_path.exists():
            log.warning(f"[MISSING] {entry['file']}")
            continue

        try:
            patch = json.loads(patch_file_path.read_text(encoding="utf-8"))
            success = False
            if isinstance(patch, list):
                success = apply_list_patch(patch, entry.get("target", patch_file_path.name))
            else:
                success = apply_gameplay_patch(patch, entry["file"])

            if success:
                applied_list.append({"patch": entry["file"], "time": datetime.now().isoformat()})
        except Exception as e:
            log.error(f"Error {entry['file']}: {e}")

    # Summary
    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_FILE.write_text(json.dumps(applied_list, indent=2))

if __name__ == "__main__":
    main()
