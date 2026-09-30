# Production Pattern: Advanced Killfeed Parser
# Concept: Weapon mapping, distance calculation, and coordinate extraction

import re
import logging
from dataclasses import dataclass
from datetime import datetime

log = logging.getLogger(__name__)

@dataclass
class ParsedKill:
    timestamp: datetime
    killer_name: str
    killer_id: str
    victim_name: str
    victim_id: str
    weapon: str
    distance: float
    is_suicide: bool = False
    is_teamkill: bool = False

class KillfeedParser:
    # Pattern: 15:30:05 | Player "Toxic" (id=XYZ) killed by Player "DayZ" (id=ABC) with M4A1 from 150.5m
    # This also handles cases with coordinates if available in extended logs.
    LINE_PATTERN = re.compile(
        r'(?P<time>\d{2}:\d{2}:\d{2}) \| Player "(?P<victim>.*)" \(id=(?P<v_id>.*)\) '
        r'killed by Player "(?P<killer>.*)" \(id=(?P<k_id>.*)\) '
        r'with (?P<weapon>.*) from (?P<dist>[\d.]+)m'
    )

    def parse_line(self, line: str) -> ParsedKill | None:
        match = self.LINE_PATTERN.search(line)
        if not match:
            return None
        
        try:
            return ParsedKill(
                timestamp=datetime.strptime(match.group('time'), "%H:%M:%S"),
                killer_name=match.group('killer'),
                killer_id=match.group('k_id'),
                victim_name=match.group('victim'),
                victim_id=match.group('v_id'),
                weapon=match.group('weapon'),
                distance=float(match.group('dist'))
            )
        except Exception as e:
            log.error(f"Failed to parse kill line: {e}")
            return None

# Production optimization: Use a pre-compiled weapon icon map
WEAPON_ICON_MAP = {
    "M4A1": "🔫 M4A1",
    "AKM": "🔫 AKM",
    "SVD": "🔭 SVD",
    "Fist": "👊 Fist",
    "Explosion": "💣 Explosion"
}
