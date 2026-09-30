#!/usr/bin/env python3
import hashlib
import os
from pathlib import Path


def get_hashes(directory: Path) -> dict[str, str]:
    hashes = {}
    if not directory.exists():
        return hashes
    for root, _, files in os.walk(directory):
        for file in files:
            full_path = Path(root) / file
            rel_path = str(full_path.relative_to(directory))
            with open(full_path, "rb") as f:
                hashes[rel_path] = hashlib.sha256(f.read()).hexdigest()
    return hashes


def compare(baseline_dir: Path, target_dir: Path):
    baseline_hashes = get_hashes(baseline_dir)
    target_hashes = get_hashes(target_dir)

    modified = []
    added = []
    removed = []

    for rel_path, h_target in target_hashes.items():
        if rel_path in baseline_hashes:
            if h_target != baseline_hashes[rel_path]:
                modified.append(rel_path)
        else:
            added.append(rel_path)

    for rel_path in baseline_hashes:
        if rel_path not in target_hashes:
            removed.append(rel_path)

    return modified, added, removed


if __name__ == "__main__":
    from src.mildlyawesome.config import get_settings
    settings = get_settings()
    CHRONOS_ROOT = settings.chronos_root
    baseline = CHRONOS_ROOT / "staging/baselines/dz_128/dayzOffline.chernarusplus"
    
    # Backup dir is external, but let's try to base it or use env
    # Assuming backups act like a sibling to the repo or driven by env
    BACKUP_ROOT = os.getenv("BACKUP_ROOT", str(CHRONOS_ROOT.parent / "backup_orig_tony"))
    target = Path(BACKUP_ROOT) / "dayzxb_missions/dayzOffline.chernarusplus"

    mod, add, rem = compare(baseline, target)

    report = ["# Tony's Backup vs Vanilla 1.28 Diff Report", ""]
    report.append("## Summary")
    report.append(f"- **Modified Files:** {len(mod)}")
    report.append(f"- **Added Files:** {len(add)}")
    report.append(f"- **Removed Files:** {len(rem)}")
    report.append("")

    if mod:
        report.append("## Modified Files")
        for f in sorted(mod):
            report.append(f"- `{f}`")
        report.append("")

    if add:
        report.append("## Added Files")
        for f in sorted(add):
            report.append(f"- `{f}`")
        report.append("")

    if rem:
        report.append("## Removed Files (Vanilla files missing in backup)")
        for f in sorted(rem):
            report.append(f"- `{f}`")

    out_file = Path(CHRONOS_ROOT) / "tony_patch_diff.md"
    with open(out_file, "w") as f:
        f.write("\n".join(report))

    print(f"Report written to {out_file}")
