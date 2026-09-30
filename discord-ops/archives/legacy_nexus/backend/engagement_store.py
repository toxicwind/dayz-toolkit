import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite

log = logging.getLogger("dayz-discord-ops.engagement")


@dataclass
class EngagementEvent:
    id: int
    user_id: int
    user_name: str
    action_type: str
    points: int
    timestamp: str


class EngagementStore:
    def __init__(self, db_path: str = "state/ezstreet/engagement.db"):
        self.db_path = db_path
        self._ready = asyncio.Event()

    async def initialize(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS points_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    user_name TEXT,
                    action_type TEXT NOT NULL,
                    points INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    user_name TEXT,
                    total_points INTEGER DEFAULT 0,
                    rank_tier TEXT DEFAULT 'Survivor',
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
        self._ready.set()
        log.info(f"EngagementStore initialized at {self.db_path}")

    async def add_points(self, user_id: int, user_name: str, action: str, points: int) -> int:
        await self._ready.wait()
        async with aiosqlite.connect(self.db_path) as db:
            # Add ledger entry
            await db.execute(
                "INSERT INTO points_ledger (user_id, user_name, action_type, points) VALUES (?, ?, ?, ?)",
                (user_id, user_name, action, points),
            )
            # Update total
            await db.execute(
                """
                INSERT INTO user_profiles (user_id, user_name, total_points, last_active)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    total_points = total_points + ?,
                    user_name = ?,
                    last_active = CURRENT_TIMESTAMP
            """,
                (user_id, user_name, points, points, user_name),
            )
            await db.commit()
            return points

    async def get_leaderboard(self, limit: int = 10) -> list[dict[str, Any]]:
        await self._ready.wait()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM user_profiles ORDER BY total_points DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


store = EngagementStore()
