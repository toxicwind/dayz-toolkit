from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from pydantic import BaseModel

from src.mildlyawesome.core.database import Database
from src.mildlyawesome.services.spawn_manager import SpawnManager

log = logging.getLogger("mildlyawesome.services.trader")

class TraderItem(BaseModel):
    name: str
    classname: str
    price: float
    category: str = "General"

class TraderService:
    """Hardened logic for the server trader system."""
    
    def __init__(self, db: Database, spawn_mgr: SpawnManager, csv_path: str):
        self.db = db
        self.spawn_mgr = spawn_mgr
        self.csv_path = Path(csv_path)
        self.items: List[TraderItem] = []
        self._load_items()

    def _load_items(self):
        if not self.csv_path.exists():
            log.warning(f"Trader CSV not found: {self.csv_path}")
            return

        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    classname = row.get('Classname', '').strip()
                    if not classname or 'No exact match' in classname:
                        continue
                    
                    try:
                        price = float(row.get('Buy Price', 0).replace(',', ''))
                    except:
                        price = 0.0

                    self.items.append(TraderItem(
                        name=row.get('Item Name', 'Unknown'),
                        classname=classname,
                        price=price,
                        category=row.get('Category', 'General')
                    ))
            log.info(f"Loaded {len(self.items)} trader items.")
        except Exception as e:
            log.error(f"Failed to load trader items: {e}")

    def search_items(self, query: str) -> List[TraderItem]:
        query = query.lower()
        return [i for i in self.items if query in i.name.lower() or query in i.classname.lower()][:25]

    async def purchase_item(self, org_id: str, user_id: str, gamertag: str, item: TraderItem, pos: tuple[float, float, float]) -> Dict[str, Any]:
        """Executes a purchase: check balance -> subtract -> queue spawn -> log."""
        balance = await self.db.get_balance(org_id, user_id)
        if balance < item.price:
            return {"success": False, "error": f"Insufficient funds. Need {item.price}, have {balance}."}

        # Subtract balance
        if not await self.db.update_balance(org_id, user_id, -item.price):
            return {"success": False, "error": "Database error during transaction."}

        # Queue spawn
        if not self.spawn_mgr.queue_spawn(gamertag, item.classname, pos):
            # Rollback balance
            await self.db.update_balance(org_id, user_id, item.price)
            return {"success": False, "error": "Failed to queue item for spawn. Refund issued."}

        # Log transaction
        def _sync_log():
            with self.db._conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO transactions (org_id, user_id, item_name, cost, status) VALUES (%s, %s, %s, %s, %s)",
                    (org_id, user_id, item.name, item.price, "COMPLETED")
                )
        await asyncio.to_thread(_sync_log)

        return {"success": True, "new_balance": balance - item.price}

import asyncio
