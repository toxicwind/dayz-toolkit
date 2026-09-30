from __future__ import annotations
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from src.mildlyawesome.core.database import Database

log = logging.getLogger("mildlyawesome.services.todo")

class TodoTask(BaseModel):
    id: Optional[int] = None
    task_key: Optional[str] = None
    title: str
    scope: str
    surface: str
    acceptance: str
    owner: Optional[str] = None
    priority: str = "P1"
    status: str = "ready"
    archived: bool = False
    channel_id: Optional[int] = None
    message_id: Optional[int] = None
    created_at: Optional[datetime] = None

class TodoService:
    """Hardened logic for managing server TODO tasks."""
    
    def __init__(self, db: Database):
        self.db = db

    async def get_config(self, key: str) -> Optional[str]:
        def _sync():
            with self.db._conn.cursor() as cursor:
                cursor.execute("SELECT cfg_value FROM todo_config WHERE cfg_key=%s", (key,))
                row = cursor.fetchone()
                return row["cfg_value"] if row else None
        return await asyncio.to_thread(_sync)

    async def set_config(self, key: str, value: str):
        def _sync():
            with self.db._conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO todo_config (cfg_key, cfg_value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE cfg_value=%s",
                    (key, value, value)
                )
        await asyncio.to_thread(_sync)

    async def list_tasks(self, status: Optional[str] = None, priority: Optional[str] = None, include_archived: bool = False) -> List[TodoTask]:
        def _sync():
            query = "SELECT * FROM todo_tasks WHERE 1=1"
            params = []
            if not include_archived:
                query += " AND archived=FALSE"
            if status:
                query += " AND status=%s"
                params.append(status)
            if priority:
                query += " AND priority=%s"
                params.append(priority)
            
            with self.db._conn.cursor() as cursor:
                cursor.execute(query, tuple(params))
                return [TodoTask(**row) for row in cursor.fetchall()]
        return await asyncio.to_thread(_sync)

    async def get_task_by_id(self, task_id: int) -> Optional[TodoTask]:
        def _sync():
            with self.db._conn.cursor() as cursor:
                cursor.execute("SELECT * FROM todo_tasks WHERE id=%s", (task_id,))
                row = cursor.fetchone()
                return TodoTask(**row) if row else None
        return await asyncio.to_thread(_sync)

    async def get_task_by_key(self, key: str) -> Optional[TodoTask]:
        def _sync():
            with self.db._conn.cursor() as cursor:
                cursor.execute("SELECT * FROM todo_tasks WHERE task_key=%s", (key,))
                row = cursor.fetchone()
                return TodoTask(**row) if row else None
        return await asyncio.to_thread(_sync)

    async def upsert_task_from_seed(self, data: Dict[str, Any]) -> TodoTask:
        def _sync():
            with self.db._conn.cursor() as cursor:
                # Check for existing key
                if data.get("task_key"):
                    cursor.execute("SELECT id FROM todo_tasks WHERE task_key=%s", (data["task_key"],))
                    row = cursor.fetchone()
                    if row:
                        # Update
                        cols = ", ".join([f"{k}=%s" for k in data.keys()])
                        cursor.execute(f"UPDATE todo_tasks SET {cols} WHERE id=%s", (*data.values(), row["id"]))
                        data["id"] = row["id"]
                        return TodoTask(**data)
                
                # Insert
                keys = ", ".join(data.keys())
                placeholders = ", ".join(["%s"] * len(data))
                cursor.execute(f"INSERT INTO todo_tasks ({keys}) VALUES ({placeholders})", tuple(data.values()))
                data["id"] = cursor.lastrowid
                return TodoTask(**data)
        return await asyncio.to_thread(_sync)

import asyncio
