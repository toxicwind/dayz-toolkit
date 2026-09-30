from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from src.mildlyawesome.core.database import Database

log = logging.getLogger("mildlyawesome.services.engagement")

class EngagementService:
    """Hardened logic for player engagement, streaks, and leveling."""
    
    def __init__(self, db: Database):
        self.db = db

    async def get_user(self, org_id: str, user_id: str) -> Dict[str, Any]:
        def _sync():
            with self.db._conn.cursor() as cursor:
                cursor.execute("SELECT * FROM engagement WHERE org_id=%s AND user_id=%s", (org_id, user_id))
                return cursor.fetchone()
        import asyncio
        data = await asyncio.to_thread(_sync)
        if not data:
            # Create default
            data = {
                "org_id": org_id,
                "user_id": user_id,
                "current_streak": 0,
                "best_streak": 0,
                "total_xp": 0,
                "level": 1,
                "last_activity": datetime.now(timezone.utc)
            }
            await self._save_user(data)
        return data

    async def _save_user(self, data: Dict[str, Any]):
        def _sync():
            with self.db._conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO engagement (org_id, user_id, current_streak, best_streak, total_xp, level, last_activity)
                       VALUES (%(org_id)s, %(user_id)s, %(current_streak)s, %(best_streak)s, %(total_xp)s, %(level)s, %(last_activity)s)
                       ON DUPLICATE KEY UPDATE 
                       current_streak=%(current_streak)s, best_streak=%(best_streak)s, total_xp=%(total_xp)s, 
                       level=%(level)s, last_activity=%(last_activity)s""",
                    data
                )
        import asyncio
        await asyncio.to_thread(_sync)

    async def track_activity(self, org_id: str, user_id: str, xp_gain: int = 10) -> Dict[str, Any]:
        """Updates XP and streaks for a user. Returns level_up info."""
        user = await self.get_user(org_id, user_id)
        now = datetime.now(timezone.utc)
        last_activity = user['last_activity']
        if isinstance(last_activity, str):
            last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
        
        # Streak logic
        diff = now - last_activity
        if diff < timedelta(hours=1):
            # Too soon for new streak check, but keep XP gain if desired
            pass 
        elif diff < timedelta(days=2):
            # Within 48 hours, increment streak if it's a new day
            if last_activity.day != now.day:
                user['current_streak'] += 1
                if user['current_streak'] > user['best_streak']:
                    user['best_streak'] = user['current_streak']
        else:
            # Streak broken
            user['current_streak'] = 1
        
        user['last_activity'] = now
        user['total_xp'] += xp_gain
        
        # Level logic (simplified: Level = sqrt(XP)/10)
        import math
        new_level = int(math.sqrt(user['total_xp']) / 5) + 1
        level_up = new_level > user['level']
        user['level'] = new_level
        
        await self._save_user(user)
        
        return {"level_up": level_up, "new_level": new_level, "user": user}
