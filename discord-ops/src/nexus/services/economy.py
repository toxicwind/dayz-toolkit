from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from src.mildlyawesome.core.database import Database

log = logging.getLogger("mildlyawesome.services.economy")

class EconomyService:
    """Hardened logic for server economy, banking, and credits."""
    
    def __init__(self, db: Database):
        self.db = db

    async def get_balance(self, org_id: str, user_id: str) -> float:
        return await self.db.get_balance(org_id, user_id)

    async def add_funds(self, org_id: str, user_id: str, amount: float, reason: str = "Income") -> bool:
        if amount <= 0: return False
        success = await self.db.update_balance(org_id, user_id, amount)
        if success:
            await self._log_transaction(org_id, user_id, f"Credit: {reason}", amount)
        return success

    async def subtract_funds(self, org_id: str, user_id: str, amount: float, reason: str = "Expense") -> bool:
        if amount <= 0: return False
        balance = await self.get_balance(org_id, user_id)
        if balance < amount:
            return False
            
        success = await self.db.update_balance(org_id, user_id, -amount)
        if success:
            await self._log_transaction(org_id, user_id, f"Debit: {reason}", -amount)
        return success

    async def transfer(self, org_id: str, from_user_id: str, to_user_id: str, amount: float) -> bool:
        if amount <= 0: return False
        if from_user_id == to_user_id: return False
        
        balance = await self.get_balance(org_id, from_user_id)
        if balance < amount:
            return False
            
        # Atomic-ish transfer
        if await self.db.update_balance(org_id, from_user_id, -amount):
            if await self.db.update_balance(org_id, to_user_id, amount):
                await self._log_transaction(org_id, from_user_id, f"Transfer to {to_user_id}", -amount)
                await self._log_transaction(org_id, to_user_id, f"Transfer from {from_user_id}", amount)
                return True
            else:
                # Rollback
                await self.db.update_balance(org_id, from_user_id, amount)
        return False

    async def _log_transaction(self, org_id: str, user_id: str, item_name: str, cost: float):
        def _sync():
            with self.db._conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO transactions (org_id, user_id, item_name, cost, status) VALUES (%s, %s, %s, %s, %s)",
                    (org_id, user_id, item_name, cost, "COMPLETED")
                )
        import asyncio
        await asyncio.to_thread(_sync)

    async def get_history(self, org_id: str, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        def _sync():
            with self.db._conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM transactions WHERE org_id=%s AND user_id=%s ORDER BY timestamp DESC LIMIT %s",
                    (org_id, user_id, limit)
                )
                return cursor.fetchall()
        import asyncio
        return await asyncio.to_thread(_sync)
