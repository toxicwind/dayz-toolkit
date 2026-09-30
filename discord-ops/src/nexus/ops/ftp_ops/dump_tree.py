#!/usr/bin/env python3
"""
Reliable full-tree FTP dump.

Defaults pull host/user/pass/paths from config (global + ezstreet + secrets.local).
Writes into settings.paths.ftp_dump (./backend_data/ftp_base) unless overridden.

Features:
- Directory-safe: creates parents, uses .part then rename to avoid partial files.
- Skips unchanged files when server reports a size.
- Depth-first traversal with clear logging.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Iterable, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from mildlyawesome.config import load_settings
from mildlyawesome.ftp_client import FTPClient

log = logging.getLogger("ftp.dump")


def _join(remote_parent: str, name: str) -> str:
    if remote_parent == "/":
        return f"/{name}"
    return f"{remote_parent.rstrip('/')}/{name}"


def _download_file(client: FTPClient, remote: str, local: Path) -> None:
    local.parent.mkdir(parents=True, exist_ok=True)
    tmp = local.with_suffix(local.suffix + ".part")
    if tmp.exists():
        tmp.unlink()
    if not client.download_file(remote, str(tmp)):
        raise RuntimeError(f"download failed: {remote}")
    tmp.replace(local)


def walk_and_download(client: FTPClient, remote_root: str, dest_root: Path) -> Tuple[int, int]:
    """Returns (files_downloaded, files_skipped)."""
    stack = [(remote_root, dest_root)]
    downloaded = 0
    skipped = 0
    while stack:
        remote_dir, local_dir = stack.pop()
        local_dir.mkdir(parents=True, exist_ok=True)
        entries = client.list_files(remote_dir)
        if not entries:
            log.debug("No entries for %s", remote_dir)
            continue
        for entry in entries:
            name = entry.get("name")
            if not name or name in {".", ".."}:
                continue
            is_dir = entry.get("is_dir", False)
            size = entry.get("size")
            remote_path = _join(remote_dir, name)
            local_path = local_dir / name
            if is_dir:
                stack.append((remote_path, local_path))
                continue
            if local_path.exists() and size is not None and local_path.stat().st_size == size:
                skipped += 1
                continue
            _download_file(client, remote_path, local_path)
            downloaded += 1
    return downloaded, skipped


def cli():
    parser = argparse.ArgumentParser(description="Full FTP tree dump to local folder.")
    parser.add_argument("--remote", default=None, help="Remote root path to dump (default: settings.ftp_base_path)")
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="Local destination folder (default: settings.paths.ftp_dump)",
    )
    parser.add_argument("--env", default="dev", help="Config env (default: dev)")
    parser.add_argument("--service", default="ezstreet", help="Service name (default: ezstreet)")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    settings = load_settings(env=args.env, service=args.service)
    remote_root = args.remote or settings.ftp_base_path or "/"
    dest_root = args.dest or Path(settings.ftp_dump_local_path)

    if not settings.ftp_host or not settings.ftp_user:
        raise SystemExit("FTP credentials missing; check config/secrets.local.yaml.")

    log.info("Dumping %s -> %s", remote_root, dest_root)
    client = FTPClient(settings.ftp_host, settings.ftp_port, settings.ftp_user, settings.ftp_password)
    if not client.connect():
        raise SystemExit("Failed to connect to FTP.")

    downloaded, skipped = walk_and_download(client, remote_root, dest_root)
    log.info("Dump complete. Downloaded %s, skipped %s (size match).", downloaded, skipped)


if __name__ == "__main__":
    cli()
