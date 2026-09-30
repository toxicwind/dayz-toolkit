#!/usr/bin/env python3
"""
List guild channels and highlight expected IDs for quick diagnostics.
Useful when the dashboard shows 0/n or the bot seems disconnected.
"""
from __future__ import annotations

import json
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"

EXPECTED = {
    "status": "1453978341076893868",
    "killfeed": "1453504155388874906",
    "deathfeed": "1453504309634531490",
    "changefeed": "1452830206141399071",
    "ops_category": "1454365349918277704",
    "todo": "1454568932051783918",
}


def deep_merge(src: dict, dst: dict) -> dict:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_merge(v, dst[k])
        else:
            dst[k] = v
    return dst


def load_settings():
    data: dict = {}
    for path in [
        CONFIG_DIR / "global.yaml",
        CONFIG_DIR / "services" / "ezstreet.yaml",
        CONFIG_DIR / "secrets.local.yaml",
    ]:
        if path.exists():
            deep_merge(yaml.safe_load(path.read_text()) or {}, data)
    disc = data.get("discord", {})
    return disc.get("token"), str(disc.get("guild_id", ""))


def main():
    token, guild_id = load_settings()
    if not token or not guild_id:
        raise SystemExit("Missing discord token or guild id in config.")

    session = requests.Session()
    session.headers["Authorization"] = f"Bot {token}"
    resp = session.get(f"https://discord.com/api/v10/guilds/{guild_id}/channels", timeout=10)
    resp.raise_for_status()
    channels = resp.json()

    print(f"Guild {guild_id}: {len(channels)} channels")
    by_id = {c["id"]: c for c in channels}
    for label, cid in EXPECTED.items():
        ch = by_id.get(cid)
        if not ch:
            print(f"[MISSING] {label}: {cid}")
        else:
            name = ch.get("name")
            ctype = ch.get("type")
            parent = ch.get("parent_id")
            print(f"[OK] {label}: {name} ({cid}) type={ctype} parent={parent}")

    # summarize by category
    print("\nCategories present:")
    categories = [c for c in channels if c["type"] == 4]
    for cat in categories:
        print(f"- {cat['name']} ({cat['id']})")


if __name__ == "__main__":
    main()
