import re
import logging
from typing import Optional
from .types import CombatEvent, CombatEventType

log = logging.getLogger(__name__)

class KillfeedParser:
    # Regex patterns recovered from legacy logic
    KILL_RE = re.compile(r'Player "(.+?)" \(DEAD\) \(id=(.+?) pos=<(.+?)>\) killed by Player "(.+?)" \(id=(.+?) pos=<(.+?)>\) with (.+?) from (.+?) meters')
    DIED_RE = re.compile(r'Player "(.+?)" \(DEAD\) \(id=(.+?) pos=<(.+?)>\) died from (.+)')
    SUICIDE_RE = re.compile(r'Player "(.+?)" \(DEAD\) \(id=(.+?) pos=<(.+?)>\) committed suicide')
    EXPLOSION_RE = re.compile(r'Player "(.+?)" \(DEAD\) \(id=(.+?) pos=<(.+?)>\) killed by explosion \((.+)\)')
    ZOMBIE_RE = re.compile(r'Player "(.+?)" \(DEAD\) \(id=(.+?) pos=<(.+?)>\) killed by (.+)') # Fallback for zombie/animal

    def parse_line(self, timestamp: str, line: str) -> Optional[CombatEvent]:
        # Implementation of parsing logic
        if "killed by Player" in line:
            m = self.KILL_RE.search(line)
            if m:
                return CombatEvent(
                    timestamp=timestamp,
                    event_type=CombatEventType.KILL,
                    victim_name=m.group(1), victim_id=m.group(2), victim_pos=m.group(3),
                    killer_name=m.group(4), killer_id=m.group(5), killer_pos=m.group(6),
                    weapon=m.group(7), distance=float(m.group(8)),
                    raw=line
                )
        elif "died from" in line:
            m = self.DIED_RE.search(line)
            if m:
                return CombatEvent(
                    timestamp=timestamp,
                    event_type=CombatEventType.FALL if "falling" in m.group(4) else CombatEventType.DEATH,
                    victim_name=m.group(1), victim_id=m.group(2), victim_pos=m.group(3),
                    raw=line
                )
        elif "committed suicide" in line:
            m = self.SUICIDE_RE.search(line)
            if m:
                return CombatEvent(
                    timestamp=timestamp,
                    event_type=CombatEventType.SUICIDE,
                    victim_name=m.group(1), victim_id=m.group(2), victim_pos=m.group(3),
                    raw=line
                )
        return None
