#!/usr/bin/env python3
"""Build and launch the DayZ Discord Ops stack with docker compose."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def run(cmd: list[str], *, check: bool = True) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=check)


def main() -> None:
    if shutil.which("docker") is None:
        sys.exit("docker CLI is required but not found in PATH.")

    compose_cmd = ["docker", "compose"]
    if subprocess.run(compose_cmd + ["version"], capture_output=True).returncode != 0:
        sys.exit("docker compose command failed. Please install Docker Compose v2+.")

    if not ENV_PATH.exists():
        sys.exit(f"Missing {ENV_PATH}. Copy .env.example -> .env and configure secrets first.")

    print("==> Building local image")
    run(compose_cmd + ["build", "dayz-discord-bot"])

    print("==> Starting MySQL (if enabled) and bot containers")
    run(compose_cmd + ["up", "-d", "mysql", "dayz-discord-bot"])

    print("==> Current status")
    run(compose_cmd + ["ps"])

    print("==> Tail bot logs (Ctrl+C to stop)")
    try:
        run(compose_cmd + ["logs", "-f", "--tail", "50", "dayz-discord-bot"], check=False)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
