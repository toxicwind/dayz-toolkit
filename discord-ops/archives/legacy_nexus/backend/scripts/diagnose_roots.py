#!/usr/bin/env python3
"""
Diagnose DayZ console FTP root confusion.

Compares the two mission roots found in the FTP dump:
- staging/nitrado_ftp_dump/dayzxb_missions/dayzOffline.chernarusplus
- staging/nitrado_ftp_dump/ezstreet/dayzxb_missions/dayzOffline.chernarusplus

Outputs a Markdown report highlighting:
- Which roots exist
- Object spawner wiring (cfggameplay.json WorldsData.objectSpawnersArr)
- File presence deltas (only in base vs only in nested vs different hashes)
- Server config log recency (dayzxb/config/server.log per root)

The report is written to docs/ops/active_root_report.md by default and also
printed to stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DUMP = REPO_ROOT / "staging" / "nitrado_ftp_dump"
DEFAULT_MISSION = "dayzOffline.chernarusplus"
DEFAULT_OUT = REPO_ROOT / "docs" / "ops" / "active_root_report.md"


def sha1(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def list_files(root: Path) -> dict[Path, Path]:
    return {p.relative_to(root): p for p in root.rglob("*") if p.is_file()}


def cfggameplay_summary(path: Path) -> tuple[int, list[str]]:
    try:
        data = json.loads(path.read_text())
        arr = data.get("WorldsData", {}).get("objectSpawnersArr", [])
        return len(arr), [str(x) for x in arr[:10]]
    except Exception:
        return 0, []


def latest_log(config_root: Path) -> tuple[str, int]:
    log_path = config_root / "server.log"
    if log_path.exists():
        return (log_path.name, int(log_path.stat().st_mtime))
    return ("(missing)", 0)


def compare_roots(base_root: Path, nested_root: Path) -> tuple[list[Path], list[Path], list[Path]]:
    base_files = list_files(base_root) if base_root.exists() else {}
    nested_files = list_files(nested_root) if nested_root.exists() else {}

    only_base = []
    only_nested = []
    different = []

    all_keys = set(base_files) | set(nested_files)
    for rel in sorted(all_keys):
        b = base_files.get(rel)
        n = nested_files.get(rel)
        if b and not n:
            only_base.append(rel)
        elif n and not b:
            only_nested.append(rel)
        elif sha1(b) != sha1(n):
            different.append(rel)
    return only_base, only_nested, different


def render_report(args, only_base, only_nested, different, base_obj, nested_obj, base_cfg, nested_cfg):
    lines = []
    lines.append("# Active mission root diagnosis")
    lines.append("")
    lines.append(f"- Dump root: `{args.dump_root}`")
    lines.append(f"- Mission: `{args.mission}`")
    lines.append("")
    lines.append("## Roots")
    lines.append(
        f"- Base root: `{args.dump_root}/dayzxb_missions/{args.mission}` ({'present' if args.base_root.exists() else 'missing'})"
    )
    lines.append(
        f"- Nested ezstreet root: `{args.dump_root}/ezstreet/dayzxb_missions/{args.mission}` ({'present' if args.nested_root.exists() else 'missing'})"
    )
    lines.append("")
    lines.append("## Object spawner wiring (cfggameplay.json)")
    lines.append(f"- Base: {base_obj[0]} entries; sample: {base_obj[1]}")
    lines.append(f"- Nested: {nested_obj[0]} entries; sample: {nested_obj[1]}")
    lines.append("")
    lines.append("## Config server.log recency")
    lines.append(f"- Base config: {base_cfg[0]}")
    lines.append(f"- Nested config: {nested_cfg[0]}")
    lines.append("")
    lines.append("## File deltas")
    lines.append(f"- Only in base root: {len(only_base)} files")
    lines.append(f"- Only in nested root: {len(only_nested)} files")
    lines.append(f"- Present in both but different hash: {len(different)} files")
    lines.append("")
    if only_nested:
        lines.append("### Examples only in nested root (ezstreet)")
        for rel in only_nested[:20]:
            lines.append(f"- {rel}")
        lines.append("")
    if only_base:
        lines.append("### Examples only in base root")
        for rel in only_base[:20]:
            lines.append(f"- {rel}")
        lines.append("")
    if different:
        lines.append("### Examples differing between roots")
        for rel in different[:20]:
            lines.append(f"- {rel}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Diagnose which mission root is actually populated in the FTP dump.")
    parser.add_argument("--dump-root", type=Path, default=DEFAULT_DUMP, help="Path to staging/nitrado_ftp_dump")
    parser.add_argument(
        "--mission", default=DEFAULT_MISSION, help="Mission folder name (default: dayzOffline.chernarusplus)"
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Markdown report path")
    args = parser.parse_args()

    args.base_root = args.dump_root / "dayzxb_missions" / args.mission
    args.nested_root = args.dump_root / "ezstreet" / "dayzxb_missions" / args.mission
    args.base_cfg_root = args.dump_root / "dayzxb" / "config"
    args.nested_cfg_root = args.dump_root / "ezstreet" / "dayzxb" / "config"

    only_base, only_nested, different = compare_roots(args.base_root, args.nested_root)

    base_obj = cfggameplay_summary(args.base_root / "cfggameplay.json")
    nested_obj = cfggameplay_summary(args.nested_root / "cfggameplay.json")

    base_cfg = latest_log(args.base_cfg_root)
    nested_cfg = latest_log(args.nested_cfg_root)

    report = render_report(args, only_base, only_nested, different, base_obj, nested_obj, base_cfg, nested_cfg)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report)
    print(report)


if __name__ == "__main__":
    main()
