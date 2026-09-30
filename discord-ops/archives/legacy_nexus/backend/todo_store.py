import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite

log = logging.getLogger("dayz-discord-ops.todo")


@dataclass
class TodoTask:
    id: int
    content: str
    status: str
    priority: str
    owner: str | None
    message_id: int | None
    channel_id: int | None
    created_at: str
    updated_at: str


class TodoStore:
    def __init__(self, db_path: str = "state/ezstreet/todo.db"):
        self.db_path = db_path
        self._ready = asyncio.Event()

    async def initialize(self):
        """Initialize the database schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'normal',
                    owner TEXT,
                    message_id INTEGER,
                    channel_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS task_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    action TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    author TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(task_id) REFERENCES tasks(id)
                )
            """)
            await db.commit()
        self._ready.set()
        log.info(f"TodoStore initialized at {self.db_path}")

    async def add_task(self, content: str, priority: str = "normal", owner: str | None = None) -> int:
        await self._ready.wait()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO tasks (content, priority, owner, status) VALUES (?, ?, ?, 'pending')",
                (content, priority, owner),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_tasks(self, status: str | None = None) -> list[dict[str, Any]]:
        await self._ready.wait()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM tasks"
            params = []
            if status:
                query += " WHERE status = ?"
                params.append(status)
            query += " ORDER BY created_at DESC"

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_task_by_message_id(self, message_id: int) -> dict[str, Any] | None:
        await self._ready.wait()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM tasks WHERE message_id = ?", (message_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def update_task(self, task_id: int, **kwargs) -> bool:
        await self._ready.wait()
        valid_fields = {"content", "status", "priority", "owner", "message_id", "channel_id"}
        updates = []
        params = []

        for k, v in kwargs.items():
            if k in valid_fields:
                updates.append(f"{k} = ?")
                params.append(v)

        if not updates:
            return False

        params.append(task_id)
        updates.append("updated_at = CURRENT_TIMESTAMP")

        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor.rowcount > 0

    async def delete_task(self, task_id: int) -> bool:
        await self._ready.wait()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            await db.commit()
            return cursor.rowcount > 0


# Global instance
store = TodoStore()
