from __future__ import annotations

import re
import logging
from typing import Any, Dict, Optional
from datetime import datetime

from src.mildlyawesome.core.types import LogEntry, LogType, ActivityType, PlayerIdentity

log = logging.getLogger("mildlyawesome.services.log-parser")

# Regex Patterns extracted from DayZ-Python-Scripts-And-Tools
PATTERNS = {
    "connection": re.compile(
        r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\)\s*is connected'
    ),
    "disconnection": re.compile(
        r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\)\s*has been disconnected'
    ),
    "unconscious": re.compile(
        r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\s*pos=<(?P<x>[0-9.-]+),\s*(?P<y>[0-9.-]+),\s*(?P<z>[0-9.-]+)>\)\s*is unconscious'
    ),
    "conscious": re.compile(
        r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\s*pos=<(?P<x>[0-9.-]+),\s*(?P<y>[0-9.-]+),\s*(?P<z>[0-9.-]+)>\)\s*regained consciousness'
    ),
    "suicide": re.compile(
        r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*(?:\(DEAD\)\s*)?\(id=(?P<player_id>[A-Fa-f0-9-]+)(?:\s*pos=<(?P<x>[0-9.-]+),\s*(?P<y>[0-9.-]+),\s*(?P<z>[0-9.-]+)>)?\)\s*committed suicide'
    ),
    "respawn": re.compile(
        r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(DEAD\)\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\s*pos=<(?P<x>[0-9.-]+),\s*(?P<y>[0-9.-]+),\s*(?P<z>[0-9.-]+)>\)\s*is choosing to respawn'
    ),
    "hit": re.compile(
        r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<victim_name>[^"]+?)"\s*(?:\(DEAD\)\s*)?\(id=(?P<victim_id>[A-Fa-f0-9-]+)\s*pos=<(?P<victim_x>[0-9.-]+),\s*(?P<victim_y>[0-9.-]+),\s*(?P<victim_z>[0-9.-]+)>\)\s*\[HP:\s*(?P<victim_hp>[0-9.]+)?\]\s*hit by Player\s*"(?P<attacker_name>[^"]+?)"\s*\(id=(?P<attacker_id>[A-Fa-f0-9-]+)\s*pos=<(?P<attacker_x>[0-9.-]+),\s*(?P<attacker_y>[0-9.-]+),\s*(?P<attacker_z>[0-9.-]+)>\)\s*into\s*(?P<hit_location>[^(]+)\((?P<hit_location_id>\d+)\)\s*for\s*(?P<damage>[0-9.]+)\s+damage\s*\((?P<ammo>[^)]+)\)(?:\s*with\s+(?P<weapon>[^\s]+)(?:\s+from\s+(?P<distance>[0-9.]+)\s+meters)?)?'
    ),
    "kill": re.compile(
        r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<victim_name>[^"]+?)"\s*\(DEAD\)\s*\(id=(?P<victim_id>[A-Fa-f0-9-]+)\s*pos=<(?P<victim_x>[0-9.-]+),\s*(?P<victim_y>[0-9.-]+),\s*(?P<victim_z>[0-9.-]+)>\)\s*killed by Player\s*"(?P<attacker_name>[^"]+?)"\s*\(id=(?P<attacker_id>[A-Fa-f0-9-]+)\s*pos=<(?P<attacker_x>[0-9.-]+),\s*(?P<attacker_y>[0-9.-]+),\s*(?P<attacker_z>[0-9.-]+)>\)\s*with\s*(?P<weapon>[^\s]+)\s*from\s*(?P<distance>[0-9.]+)\s+meters'
    ),
    "env_hit": re.compile(
        r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\s*pos=<(?P<x>[0-9.-]+),\s*(?P<y>[0-9.-]+),\s*(?P<z>[0-9.-]+)>\)\s*\[HP:\s*(?P<hp>[0-9.]+)?\]\s+hit by\s+(?P<attacker>[^\s]+)\s+with\s+(?P<weapon>[^\s]+)'
    ),
    "placed": re.compile(
        r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\s*pos=<(?P<x>[0-9.-]+),\s*(?P<y>[0-9.-]+),\s*(?P<z>[0-9.-]+)>\)\s+placed\s+(?P<structure>.+)'
    ),
    "built": re.compile(
        r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\s*pos=<(?P<x>[0-9.-]+),\s*(?P<y>[0-9.-]+),\s*(?P<z>[0-9.-]+)>\)\s*(?P<action>Built|Dismantled)\s+(?P<structure>[^\s]+)\s+(?P<on_or_from>on|from)\s+(?P<parent>[^\s]+)\s+with\s+(?P<tool>[^\s]+)$'
    ),
    "chat": re.compile(
        r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\)\s*:\s*(?P<message>.+)'
    ),
}

ACTIVITY_MAP = {
    "connection": ActivityType.CONNECT,
    "disconnection": ActivityType.DISCONNECT,
    "unconscious": ActivityType.CHAT, 
    "conscious": ActivityType.CHAT,
    "suicide": ActivityType.KILL,
    "respawn": ActivityType.CONNECT,
    "hit": ActivityType.CHAT,
    "kill": ActivityType.KILL,
    "env_hit": ActivityType.CHAT,
    "placed": ActivityType.ECONOMY,
    "built": ActivityType.ECONOMY,
    "chat": ActivityType.CHAT,
}

class DayZLogParser:
    def __init__(self, server_date: Optional[str] = None):
        self.server_date = server_date or datetime.now().strftime("%Y-%m-%d")

    def _parse_timestamp(self, time_str: str) -> datetime:
        try:
            return datetime.strptime(f"{self.server_date} {time_str}", "%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.now()

    def parse_line(self, line: str, log_type: LogType = LogType.ADM) -> Optional[LogEntry]:
        line = line.strip()
        if not line:
            return None

        for event_key, pattern in PATTERNS.items():
            match = pattern.match(line)
            if match:
                data = match.groupdict()
                timestamp = self._parse_timestamp(data.get("time", "00:00:00"))
                activity_type = ACTIVITY_MAP.get(event_key, ActivityType.CHAT)
                
                return LogEntry(
                    timestamp=timestamp,
                    log_type=log_type,
                    activity_type=activity_type,
                    message=line,
                    metadata=data,
                    raw_line=line
                )

        return None
