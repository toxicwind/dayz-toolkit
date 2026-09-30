#!/usr/bin/env python3
"""
One-off seeder for the #server-todo channel.

Reads discord token/guild from config/secrets.local.yaml and config/services/ezstreet.yaml,
ensures the TODO rules + seed_tasks.yaml cards are posted to the configured channel
(defaults to ops category channel id if not provided).

Intended for quick reruns when the bot is offline or hot-reload is disabled.
"""
from __future__ import annotations

import json
import sqlite3
import urllib.parse
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DB_PATH = ROOT / "state" / "todo.db"
SEED_PATH = ROOT / "seed_tasks.yaml"

STATUS_TO_EMOJI = {"ready": "🟦", "in_progress": "🟨", "blocked": "🟥", "done": "🟩", "dropped": "⛔️"}

RULES_MESSAGE = (
    "**SERVER TODO (status is emoji-driven; no discussion here)**\n\n"
    "**How to use this channel**\n"
    "* This channel is for task cards only. Ask questions in **#server-chat**.\n"
    "* Each task is one message posted by the bot.\n"
    "* Update status by reacting with exactly one status emoji.\n\n"
    "**Status key (Unicode only)**\n"
    "* 🟥 Blocked (needs info / needs files / can’t proceed)\n"
    "* 🟨 In progress\n"
    "* 🟩 Done\n"
    "* 🟦 Ready / queued (default)\n"
    "* ⛔️ Dropped / won’t do\n\n"
    "**Priority (optional)**\n"
    "* 🔥 P0 (server unplayable)\n"
    "* ⚠️ P1 (economy/feel issues)\n"
    "* ✳️ P2 (nice-to-have)\n\n"
    "**Owner (optional)**\n"
    "* 👤 Tony owns answer / decision\n"
    "* 🧑‍💻 Chris implementing\n\n"
    "**Rule**: If a task is 🟥 Blocked, the next message in #server-chat must answer the blocker."
)


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
    token = disc.get("token")
    guild_id = disc.get("guild_id")
    status_channel = disc.get("status_channel_id")
    return token, guild_id, status_channel


def ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_key TEXT UNIQUE,
            title TEXT NOT NULL,
            scope TEXT NOT NULL,
            surface TEXT NOT NULL,
            acceptance TEXT NOT NULL,
            owner TEXT,
            priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ready',
            archived INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TRIGGER IF NOT EXISTS trg_tasks_updated
        AFTER UPDATE ON tasks
        FOR EACH ROW
        BEGIN
            UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
        CREATE TABLE IF NOT EXISTS task_messages (
            task_id INTEGER PRIMARY KEY,
            channel_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()
    return conn


def post(session: requests.Session, channel_id: str, content: str) -> str:
    resp = session.post(
        f"https://discord.com/api/v10/channels/{channel_id}/messages",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"content": content}),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def react(session: requests.Session, channel_id: str, message_id: str, emoji: str) -> None:
    enc = urllib.parse.quote(emoji)
    resp = session.put(
        f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}/reactions/{enc}/@me",
        timeout=10,
    )
    resp.raise_for_status()


def main():
    token, guild_id, status_channel = load_settings()
    if not token:
        raise SystemExit("Missing discord token in config.")

    # TODO channel is already created; hardcode id so we don't need manage-channels scope.
    todo_channel_id = "1454568932051783918"

    session = requests.Session()
    session.headers["Authorization"] = f"Bot {token}"

    conn = ensure_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO config(key, value) VALUES('todo_channel_id', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (todo_channel_id,),
    )

    # post rules if missing
    cur.execute("SELECT value FROM config WHERE key='todo_rules_message_id'")
    row = cur.fetchone()
    if not row:
        rid = post(session, todo_channel_id, RULES_MESSAGE)
        try:
            session.put(f"https://discord.com/api/v10/channels/{todo_channel_id}/pins/{rid}", timeout=5)
        except requests.RequestException:
            pass
        cur.execute(
            "INSERT INTO config(key, value) VALUES('todo_rules_message_id', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (rid,),
        )
        print("Posted rules.")
    else:
        print("Rules already recorded; skipping.")

    payload = yaml.safe_load(SEED_PATH.read_text()) or {}
    created = 0
    for item in payload.get("tasks", []):
        cur.execute("SELECT id FROM tasks WHERE task_key = ?", (item.get("key"),))
        row = cur.fetchone()
        if not row:
            cur.execute(
                """
                INSERT INTO tasks(task_key,title,scope,surface,acceptance,owner,priority,status)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    item.get("key"),
                    item["title"],
                    item["scope"],
                    item["surface"],
                    item["acceptance"],
                    item.get("owner"),
                    item.get("priority", "P1"),
                    item.get("status", "ready"),
                ),
            )
            task_id = cur.lastrowid
        else:
            task_id = row[0]
        cur.execute("SELECT message_id FROM task_messages WHERE task_id = ?", (task_id,))
        msg_row = cur.fetchone()
        if msg_row:
            continue
        header = f"{STATUS_TO_EMOJI.get(item.get('status', 'ready'), '🟦')} [{item.get('priority', 'P1')}] {item['title']}"
        body = (
            f"Scope: {item['scope']}\n"
            f"Surface: {item['surface']}\n"
            f"Acceptance: {item['acceptance']}\n"
            f"Owner: {item.get('owner', '-')}"
        )
        mid = post(session, todo_channel_id, f"{header}\n{body}")
        react(session, todo_channel_id, mid, STATUS_TO_EMOJI.get(item.get("status", "ready"), "🟦"))
        cur.execute(
            "INSERT OR REPLACE INTO task_messages(task_id, channel_id, message_id) VALUES(?,?,?)",
            (task_id, todo_channel_id, mid),
        )
        created += 1

    conn.commit()
    conn.close()
    print(f"Seed complete: {created} task cards posted.")


if __name__ == "__main__":
    main()
