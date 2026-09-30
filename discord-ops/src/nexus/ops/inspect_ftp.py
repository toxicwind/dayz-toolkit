#!/usr/bin/env python3
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from bot.config import load_settings
from bot.ftp_client import FTPClient


def inspect_ftp(depth: int = 2):
    settings = load_settings()
    client = FTPClient(settings.ftp_host, settings.ftp_port, settings.ftp_user, settings.ftp_password)
    if not client.connect():
        print("FTP connect failed")
        return

    def walk(prefix: str, remote: str, d: int):
        if d > depth:
            return
        entries = client.list_files(remote)
        print(f"{prefix}[{remote}] {len(entries)} entries")
        for e in entries:
            name = e.get("name")
            is_dir = e.get("is_dir")
            size = e.get("size")
            if is_dir:
                walk(prefix + "  ", f"{remote.rstrip('/')}/{name}", d + 1)
            else:
                sz = f" ({size}b)" if size is not None else ""
                print(f"{prefix}  - {name}{sz}")

    walk("", settings.ftp_base_path or "/", 0)


if __name__ == "__main__":
    inspect_ftp()
