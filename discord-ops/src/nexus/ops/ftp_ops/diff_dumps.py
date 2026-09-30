#!/usr/bin/env python3
"""
Compare two DayZ mission trees (e.g., live FTP dump vs patched staging).

Default paths:
  left  = backend_data/ftp_base      (live dump)
  right = backend_data/staging       (patched output)

Outputs a concise summary:
  - Added/removed files
  - Changed files (size or hash)
  - Changed directories (presence only)
  - Optionally, emit a CSV-friendly list for automation.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
from typing import Dict, Tuple, List

ROOT = Path(__file__).resolve().parents[2]


def hash_file(path: Path, buf_size: int = 256 * 1024) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            chunk = f.read(buf_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def snapshot(root: Path) -> Dict[str, Tuple[int, str]]:
    """
    Return map: relative_path -> (size, sha1)
    Directories are stored with size = -1 and hash = "" to track presence.
    """
    result: Dict[str, Tuple[int, str]] = {}
    if not root.exists():
        return result
    for p in root.rglob("*"):
        rel = p.relative_to(root).as_posix()
        if p.is_dir():
            result[rel + "/"] = (-1, "")
        elif p.is_file():
            try:
                size = p.stat().st_size
            except OSError:
                continue
            try:
                digest = hash_file(p)
            except OSError:
                digest = "ERR"
            result[rel] = (size, digest)
    return result


def diff_maps(
    left: Dict[str, Tuple[int, str]], right: Dict[str, Tuple[int, str]]
) -> Tuple[List[str], List[str], List[str]]:
    added: List[str] = []
    removed: List[str] = []
    changed: List[str] = []
    left_keys = set(left.keys())
    right_keys = set(right.keys())
    for k in sorted(left_keys - right_keys):
        removed.append(k)
    for k in sorted(right_keys - left_keys):
        added.append(k)
    for k in sorted(left_keys & right_keys):
        if left[k] != right[k]:
            changed.append(k)
    return added, removed, changed


def format_section(title: str, items: List[str]):
    if not items:
        print(f"{title}: none")
        return
    print(f"{title} ({len(items)}):")
    for it in items:
        print(f"  - {it}")


def main():
    parser = argparse.ArgumentParser(description="Diff two mission trees (hash-based).")
    parser.add_argument("--left", type=Path, default=ROOT / "backend_data" / "ftp_base", help="Reference tree (e.g., live dump)")
    parser.add_argument("--right", type=Path, default=ROOT / "backend_data" / "staging", help="Patched tree")
    parser.add_argument("--csv", action="store_true", help="Print CSV lines: status,path")
    args = parser.parse_args()

    left_map = snapshot(args.left)
    right_map = snapshot(args.right)

    added, removed, changed = diff_maps(left_map, right_map)

    if args.csv:
        for path in removed:
            print(f"removed,{path}")
        for path in added:
            print(f"added,{path}")
        for path in changed:
            print(f"changed,{path}")
        return

    print(f"Compared {len(left_map)} (left) vs {len(right_map)} (right)")
    format_section("Added in right", added)
    format_section("Removed from right", removed)
    format_section("Changed", changed)


if __name__ == "__main__":
    main()
