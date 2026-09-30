import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

log = logging.getLogger("dayz-discord-ops.parser")


@dataclass
class ADMEvent:
    timestamp: datetime
    event_type: str
    player_name: str
    player_id: str
    pos: tuple[float, float, float] | None = None
    data: dict[str, Any] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class ADMLogParser:
    """
    Advanced ADM Log Parser
    Handles both live streaming and batch log files.
    """

    PATTERNS = {
        "connect": re.compile(
            r'(?P<time>[\d:\-\s]+)\s*\|\s*Player\s*"(?P<player_name>[^"]+)"\s*\(id=(?P<player_id>[^)]+)\)\s*is connected'
        ),
        "disconnect": re.compile(
            r'(?P<time>[\d:\-\s]+)\s*\|\s*Player\s*"(?P<player_name>[^"]+)"\s*\(id=(?P<player_id>[^)]+)\)\s*has been disconnected'
        ),
        "hit": re.compile(
            r'(?P<time>[\d:\-\s]+)\s*\|\s*Player\s*"(?P<victim_name>[^"]+)"\s*\(id=(?P<victim_id>[^)]+)\s*pos=<(?P<v_pos>[^>]+)>\)\s*\[HP:\s*(?P<hp>[\d.]+)\].*hit by Player\s*"(?P<attacker_name>[^"]+)"\s*\(id=(?P<attacker_id>[^)]+)\s*pos=<(?P<a_pos>[^>]+)>\)\s*into\s*(?P<location>[^(]+)\((?P<loc_id>\d+)\)\s*for\s*(?P<damage>[\d.]+)\s*damage\s*\((?P<ammo>[^)]+)\)(?:\s*with\s+(?P<weapon>[^\s]+)(?:\s+from\s+(?P<dist>[\d.]+)\s+meters)?)?'
        ),
        "kill": re.compile(
            r'(?P<time>[\d:\-\s]+)\s*\|\s*Player\s*"(?P<victim_name>[^"]+)"\s*\(DEAD\)\s*\(id=(?P<victim_id>[^)]+)\s*pos=<(?P<v_pos>[^>]+)>\)\s*killed by Player\s*"(?P<attacker_name>[^"]+)"\s*\(id=(?P<attacker_id>[^)]+)\s*pos=<(?P<a_pos>[^>]+)>\)\s*with\s*(?P<weapon>[^\s]+)\s*from\s*(?P<dist>[\d.]+)\s+meters'
        ),
        "building": re.compile(
            r'(?P<time>[\d:\-\s]+)\s*\|\s*Player\s*"(?P<player_name>[^"]+)"\s*\(id=(?P<player_id>[^)]+)\s*pos=<(?P<pos>[^>]+)>\)\s*(?P<action>Built|Dismantled|repaired|packed|placed|folded)\s+(?P<structure>[^\s]+).*with\s+(?P<tool>[^\s]+)'
        ),
        "suicide": re.compile(
            r'(?P<time>[\d:\-\s]+)\s*\|\s*Player\s*"(?P<player_name>[^"]+)"\s*\(DEAD\)\s*\(id=(?P<player_id>[^)]+)\s*pos=<(?P<pos>[^>]+)>\)\s*committed suicide'
        ),
    }

    def __init__(self, base_date: datetime | None = None):
        self.base_date = base_date or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    def parse_line(self, line: str) -> ADMEvent | None:
        for event_type, pattern in self.PATTERNS.items():
            match = pattern.search(line)
            if not match:
                continue

            data = match.groupdict()
            ts_str = data.get("time", "")
            timestamp = self._parse_timestamp(ts_str)

            # Common Player Info
            p_name = data.get("player_name") or data.get("victim_name") or data.get("attacker_name")
            p_id = data.get("player_id") or data.get("victim_id") or data.get("attacker_id")

            # Position extraction
            pos = None
            if "pos" in data:
                pos = self._parse_pos(data["pos"])
            elif "v_pos" in data:
                pos = self._parse_pos(data["v_pos"])

            return ADMEvent(
                timestamp=timestamp,
                event_type=event_type,
                player_name=p_name,
                player_id=p_id,
                pos=pos,
                data=data,
            )
        return None

    @staticmethod
    def parse_log_content(content: str) -> list[dict]:
        """Static helper to parse a block of log text into dicts"""
        parser = ADMLogParser()
        events = []
        for line in content.splitlines():
            if not line.strip():
                continue
            event = parser.parse_line(line)
            if event:
                # Convert dataclass to dict for compatibility with backend.py
                evt_dict = {
                    "timestamp": event.timestamp,
                    "event_type": event.event_type,
                    "player_name": event.player_name,
                    "player_id": event.player_id,
                    "gamertag": event.player_name,  # Alias for bot compatibility
                    "data": event.data,
                }
                if event.pos:
                    evt_dict["pos_x"] = event.pos[0]
                    evt_dict["pos_y"] = event.pos[1]
                    evt_dict["pos_z"] = event.pos[2]
                events.append(evt_dict)
        return events

    def _parse_timestamp(self, ts_str: str) -> datetime:
        """Handles both YYYY-MM-DD HH:MM:SS and HH:MM:SS"""
        try:
            if "-" in ts_str and " " in ts_str:
                return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            else:
                # Just time, combine with base_date
                t = datetime.strptime(ts_str, "%H:%M:%S").time()
                return datetime.combine(self.base_date.date(), t)
        except:
            return datetime.now()

    def _parse_pos(self, pos_str: str) -> tuple[float, float, float] | None:
        try:
            parts = [float(x) for x in pos_str.replace("<", "").replace(">", "").split(",")]
            return (parts[0], parts[1], parts[2])
        except:
            return None
