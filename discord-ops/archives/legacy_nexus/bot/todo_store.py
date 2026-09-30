from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Sequence

import aiosqlite


@dataclass
class TodoTask:
    id: int
    task_key: Optional[str]
    title: str
    scope: str
    surface: str
    acceptance: str
    owner: Optional[str]
    priority: str
    status: str
    archived: bool
    channel_id: Optional[int]
    message_id: Optional[int]


class TodoStore:
    """Async SQLite helper for TODO tracking."""

    def __init__(self, db_path: Path | str = Path("state/todo.db")) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def _connect(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        return conn

    async def ensure_ready(self) -> None:
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            conn = await self._connect()
            try:
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                await conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS config (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    );

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
                await conn.commit()
                self._initialized = True
            finally:
                await conn.close()

    async def set_config(self, key: str, value: str) -> None:
        await self.ensure_ready()
        conn = await self._connect()
        try:
            await conn.execute(
                "INSERT INTO config(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            await conn.commit()
        finally:
            await conn.close()

    async def get_config(self, key: str, default: Optional[str] = None) -> Optional[str]:
        await self.ensure_ready()
        conn = await self._connect()
        try:
            cur = await conn.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = await cur.fetchone()
            return row["value"] if row else default
        finally:
            await conn.close()

    async def insert_task(self, task_data: dict[str, Any]) -> TodoTask:
        await self.ensure_ready()
        conn = await self._connect()
        try:
            cur = await conn.execute(
                """
                INSERT INTO tasks(task_key, title, scope, surface, acceptance, owner, priority, status)
                VALUES(:task_key, :title, :scope, :surface, :acceptance, :owner, :priority, :status)
                """,
                task_data,
            )
            await conn.commit()
            task_id = cur.lastrowid
        finally:
            await conn.close()
        return await self.get_task_by_id(task_id)

    async def upsert_task_from_seed(self, task_data: dict[str, Any]) -> TodoTask:
        """Insert seed task if it's missing; otherwise return existing row."""
        existing = await self.get_task_by_key(task_data.get("task_key"))
        if existing:
            return existing
        return await self.insert_task(task_data)

    async def get_task_by_id(self, task_id: int) -> Optional[TodoTask]:
        await self.ensure_ready()
        conn = await self._connect()
        try:
            cur = await conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = await cur.fetchone()
            if not row:
                return None
            mapping = await self._attach_message([row])
            return mapping[0] if mapping else None
        finally:
            await conn.close()

    async def get_task_by_key(self, task_key: Optional[str]) -> Optional[TodoTask]:
        if not task_key:
            return None
        await self.ensure_ready()
        conn = await self._connect()
        try:
            cur = await conn.execute("SELECT * FROM tasks WHERE task_key = ?", (task_key,))
            row = await cur.fetchone()
            if not row:
                return None
            mapping = await self._attach_message([row])
            return mapping[0] if mapping else None
        finally:
            await conn.close()

    async def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[TodoTask]:
        await self.ensure_ready()
        clauses = []
        params: list[Any] = []
        if not include_archived:
            clauses.append("archived = 0")
        if status:
            clauses.append("status = ?")
            params.append(status)
        if priority:
            clauses.append("priority = ?")
            params.append(priority)
        where = ""
        if clauses:
            where = "WHERE " + " AND ".join(clauses)
        query = f"SELECT * FROM tasks {where} ORDER BY priority, id"

        conn = await self._connect()
        try:
            cur = await conn.execute(query, params)
            rows = await cur.fetchall()
            return await self._attach_message(rows)
        finally:
            await conn.close()

    async def update_task_status(self, task_id: int, status: str) -> None:
        await self.ensure_ready()
        conn = await self._connect()
        try:
            await conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
            await conn.commit()
        finally:
            await conn.close()

    async def update_task_owner(self, task_id: int, owner: Optional[str]) -> None:
        await self.ensure_ready()
        conn = await self._connect()
        try:
            await conn.execute("UPDATE tasks SET owner = ? WHERE id = ?", (owner, task_id))
            await conn.commit()
        finally:
            await conn.close()

    async def update_task_priority(self, task_id: int, priority: str) -> None:
        await self.ensure_ready()
        conn = await self._connect()
        try:
            await conn.execute("UPDATE tasks SET priority = ? WHERE id = ?", (priority, task_id))
            await conn.commit()
        finally:
            await conn.close()

    async def set_task_message(self, task_id: int, channel_id: int, message_id: int) -> None:
        await self.ensure_ready()
        conn = await self._connect()
        try:
            await conn.execute(
                """
                INSERT INTO task_messages(task_id, channel_id, message_id)
                VALUES(?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    message_id = excluded.message_id
                """,
                (task_id, channel_id, message_id),
            )
            await conn.commit()
        finally:
            await conn.close()

    async def delete_task_message(self, task_id: int) -> None:
        await self.ensure_ready()
        conn = await self._connect()
        try:
            await conn.execute("DELETE FROM task_messages WHERE task_id = ?", (task_id,))
            await conn.commit()
        finally:
            await conn.close()

    async def get_task_by_message(self, message_id: int) -> Optional[TodoTask]:
        await self.ensure_ready()
        conn = await self._connect()
        try:
            cur = await conn.execute(
                """
                SELECT t.*, tm.channel_id, tm.message_id
                FROM tasks t
                JOIN task_messages tm ON tm.task_id = t.id
                WHERE tm.message_id = ?
                """,
                (message_id,),
            )
            row = await cur.fetchone()
            if not row:
                return None
            return self._row_to_task(row)
        finally:
            await conn.close()

    async def archive_tasks(self, task_ids: Sequence[int]) -> None:
        if not task_ids:
            return
        await self.ensure_ready()
        conn = await self._connect()
        try:
            placeholders = ",".join("?" for _ in task_ids)
            await conn.execute(
                f"UPDATE tasks SET archived = 1 WHERE id IN ({placeholders})",
                tuple(task_ids),
            )
            await conn.commit()
        finally:
            await conn.close()

    async def _attach_message(self, rows: Sequence[aiosqlite.Row]) -> List[TodoTask]:
        if not rows:
            return []
        ids = [row["id"] for row in rows]
        placeholders = ",".join("?" for _ in ids)
        conn = await self._connect()
        try:
            cur = await conn.execute(
                f"SELECT * FROM task_messages WHERE task_id IN ({placeholders})", ids
            )
            mapping = {row["task_id"]: row for row in await cur.fetchall()}
        finally:
            await conn.close()

        tasks: List[TodoTask] = []
        for row in rows:
            tm = mapping.get(row["id"])
            tasks.append(
                TodoTask(
                    id=row["id"],
                    task_key=row["task_key"],
                    title=row["title"],
                    scope=row["scope"],
                    surface=row["surface"],
                    acceptance=row["acceptance"],
                    owner=row["owner"],
                    priority=row["priority"],
                    status=row["status"],
                    archived=bool(row["archived"]),
                    channel_id=tm["channel_id"] if tm else None,
                    message_id=tm["message_id"] if tm else None,
                )
            )
        return tasks

    def _row_to_task(self, row: aiosqlite.Row) -> TodoTask:
        return TodoTask(
            id=row["id"],
            task_key=row["task_key"],
            title=row["title"],
            scope=row["scope"],
            surface=row["surface"],
            acceptance=row["acceptance"],
            owner=row["owner"],
            priority=row["priority"],
            status=row["status"],
            archived=bool(row["archived"]),
            channel_id=row["channel_id"],
            message_id=row["message_id"],
        )
