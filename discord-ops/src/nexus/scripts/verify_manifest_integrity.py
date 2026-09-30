#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Paths
from src.mildlyawesome.config import get_settings
settings = get_settings()

REPO_ROOT = settings.chronos_root
MANIFEST_PATH = REPO_ROOT / "backend/patcher/patches/manifest.json"
PATCHES_DIR = REPO_ROOT / "backend/patcher/patches"


def fail(msg):
    print(f"[FAIL] {msg}")
    sys.exit(1)


def main():
    print(f"Verifying integrity: {MANIFEST_PATH}")

    if not MANIFEST_PATH.exists():
        fail(f"Manifest missing at {MANIFEST_PATH}")

    try:
        with open(MANIFEST_PATH) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        fail(f"Manifest JSON invalid: {e}")

    if "patches" not in data:
        fail("Manifest missing 'patches' key")

    patches = data["patches"]
    seen_ids = set()
    errors = 0

    print(f"Scanning {len(patches)} patches...")

    for i, p in enumerate(patches):
        # File check
        p_file = p.get("file")
        if not p_file:
            print(f"[ERR] Patch #{i} missing 'file' key")
            errors += 1
            continue

        fp = PATCHES_DIR / p_file
        if not fp.exists():
            print(f"[ERR] Patch manifest references missing file: {p_file}")
            errors += 1
            continue

        # ID check (from content)
        try:
            with open(fp) as f:
                patch_content = json.load(f)

            # Patch files can be objects (with optional id) or raw JSON-Patch lists.
            if isinstance(patch_content, dict):
                pid = patch_content.get("id") or p_file
            else:
                pid = p_file  # fallback for list-based patch definitions

            if pid in seen_ids:
                print(f"[ERR] Duplicate patch ID: {pid} (in {p_file})")
                errors += 1
            else:
                seen_ids.add(pid)
        except json.JSONDecodeError:
            print(f"[ERR] Invalid JSON in patch file: {p_file}")
            errors += 1

        # Enabled check (boolean)
        if not isinstance(p.get("enabled", True), bool):
            print(f"[ERR] Patch {pid} 'enabled' is not bool")
            errors += 1

    if errors > 0:
        fail(f"Found {errors} integrity violations.")

    print("[PASS] Manifest integrity verified.")


if __name__ == "__main__":
    main()
