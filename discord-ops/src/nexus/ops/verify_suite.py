#!/usr/bin/env python3
"""
One-button verify loop for console build.

Runs in order:
 1) A2S/FTP probe (tools/platform_probe.py) to ensure config + connectivity.
 2) FTP dump (tools/ftp_ops/dump_tree.py) into backend_data/ftp_base.
 3) FTP diff vs staging (tools/ftp_ops/diff_dumps.py) if staging exists.
 4) Lint/format check (ruff) and type check (pyright).

Exits non-zero on first failure.
"""
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent


def run(cmd: list[str], name: str) -> None:
    print(f"\n=== {name} ===")
    res = subprocess.run(cmd, cwd=repo_root)
    if res.returncode != 0:
        sys.exit(res.returncode)


def main() -> None:
    run([sys.executable, "tools/platform_probe.py"], "Probe: platform (A2S/FTP)")
    run([sys.executable, "tools/ftp_ops/dump_tree.py"], "FTP dump -> backend_data/ftp_base")
    if (repo_root / "backend_data/staging").exists():
        run([sys.executable, "tools/ftp_ops/diff_dumps.py"], "FTP diff base vs staging")
    run(["bash", "tools/lint.sh"], "Lint/format (ruff)")
    run(["bash", "tools/typecheck.sh"], "Type check (pyright)")
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
