from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from src.mildlyawesome.core.database import Database

log = logging.getLogger("mildlyawesome.services.identity")

class IdentityService:
    """Hardened logic for player identity, linking, and aliasing."""
    
    def __init__(self, db: Database):
        self.db = db

    async def whois(self, org_id: str, search_query: str) -> List[Dict[str, Any]]:
        """Search for player profiles by ID or Name."""
        def _sync():
            with self.db._conn.cursor() as cursor:
                # Search by ID, name, or last known name
                query = f"%{search_query}%"
                cursor.execute(
                    """SELECT * FROM player_profiles 
                       WHERE org_id=%s AND (player_id LIKE %s OR last_known_name LIKE %s)""",
                    (org_id, query, query)
                )
                return cursor.fetchall()
        import asyncio
        return await asyncio.to_thread(_sync)

    async def link_gamertag(self, org_id: str, user_id: str, gamertag: str) -> bool:
        """Links a Discord User ID to a DayZ Gamertag."""
        def _sync():
            try:
                with self.db._conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO economy (org_id, user_id, gamertag) 
                           VALUES (%s, %s, %s)
                           ON DUPLICATE KEY UPDATE gamertag=%s""",
                        (org_id, user_id, gamertag, gamertag)
                    )
                return True
            except Exception as e:
                log.error(f"Link failed: {e}")
                return False
        import asyncio
        return await asyncio.to_thread(_sync)

    async def get_identity(self, org_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves linked identity for a Discord user."""
        return await self.db.get_user_data(org_id, user_id)
