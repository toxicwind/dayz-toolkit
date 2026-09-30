import asyncio
import logging
import re
import math
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict, Optional

from .adm_log_parser import ADMEvent
from src.mildlyawesome.core.database import Database
from .rpt_parser import RPTEvent

log = logging.getLogger("mildlyawesome.services.analytics")

# Emergent Feature Constants
HEATMAP_GRID_SIZE = 100
ECONOMY_HISTORY_SIZE = 168 # 1 week hourly


class AnalyticsEngine:
    """
    Unified Intelligence Engine.
    Combines SQL Persistence (History) with Real-Time Emergent Analysis (RAM).
    """

    def __init__(self, db: Database):
        self.db = db
        self._heatmap_data = defaultdict(int)
        self._economy_history = deque(maxlen=ECONOMY_HISTORY_SIZE)
        self._ai_anomaly_scores = defaultdict(float)
        self._player_squads = defaultdict(set)
        self._last_seen = {}
        self._combat_events = deque(maxlen=1000)

    async def get_player_survival_profile(self, org_id: str, player_id_or_name: str) -> Optional[Dict[str, Any]]:
        """
        Generates a deep survival profile for a player.
        """
        # 1. Lookup profile in DB
        def _sync_lookup():
            with self.db._conn.cursor() as cursor:
                # Search by ID or Name
                cursor.execute(
                    "SELECT * FROM player_profiles WHERE org_id=%s AND (player_id=%s OR last_known_name=%s)",
                    (org_id, player_id_or_name, player_id_or_name)
                )
                return cursor.fetchone()
        
        profile = await asyncio.to_thread(_sync_lookup)
        if not profile:
            return None

        # 2. Calculate survival metrics
        kills = profile.get('kills', 0)
        deaths = max(profile.get('deaths', 1), 1)
        kd = round(kills / deaths, 2)
        
        # Survival Score: 0-100 heuristic
        # (Kills * 2) + (KD * 5) - (Deaths * 1) + Base 20
        score = min(100, max(0, 20 + (kills * 2) + (kd * 5) - (deaths)))
        
        # Threat Level
        if score > 80: threat = "EXTREME"
        elif score > 60: threat = "HIGH"
        elif score > 40: threat = "MODERATE"
        else: threat = "LOW"

        # Pattern
        if kd > 3: pattern = "Predator"
        elif kills > 10 and deaths > 10: pattern = "Veteran"
        elif kd < 0.5: pattern = "Survivor"
        else: pattern = "Stalker"

        return {
            "name": profile['last_known_name'],
            "id": profile['player_id'],
            "score": score,
            "threat": threat,
            "pattern": pattern,
            "kills": kills,
            "deaths": profile['deaths'],
            "kd": kd,
            "last_seen": profile['last_seen']
        }

    def process_event(self, org_id: str, event: Any):
        """Processes a live event for immediate analytics."""
        try:
            ts = datetime.utcnow().isoformat()
            if isinstance(event, ADMEvent):
                if event.event_type in ["kill", "hit"]:
                    data = event.data
                    dist = float(data.get("dist", 0)) if data.get("dist") else 0.0
                    self._combat_events.append({
                        "ts": ts,
                        "killer": data.get("attacker_name", "Unknown"),
                        "victim": data.get("victim_name", "Unknown"),
                        "weapon": data.get("weapon"),
                        "dist": dist
                    })
                    # Update DB (Deferred)
                    if data.get("attacker_id") and data.get("victim_id"):
                         asyncio.create_task(self.db.increment_kill_stats(org_id, data['attacker_id'], data['victim_id']))

            elif isinstance(event, RPTEvent):
                if event.event_type == "player_connect":
                    pid = event.data.get("id") or event.data.get("name")
                    if pid:
                        self._last_seen[pid] = datetime.now().timestamp()
        except Exception as e:
            log.error(f"Analytics processing failed: {e}")
