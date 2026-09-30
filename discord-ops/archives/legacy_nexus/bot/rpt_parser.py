import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass

log = logging.getLogger("dayz-discord-ops.rpt-parser")

@dataclass
class RPTEvent:
    timestamp: datetime
    event_type: str  # 'fps', 'memory', 'search_overtime', 'hard_to_place', 'script_error', 'player_event'
    message: str
    data: Dict[str, Any]

class RPTLogParser:
    """
    DayZ RPT Log Parser
    Extracts performance metrics, diagnostics, and errors.
    """
    
    PATTERNS = {
        'fps': re.compile(r'(?P<time>[\d:]+)\s+Server FPS:\s*(?P<fps>[\d.]+)'),
        'memory': re.compile(r'Virtual Memory:\s*(?P<virt>[\d.]+)MB,\s*Physical Memory:\s*(?P<phys>[\d.]+)MB'),
        'search_overtime': re.compile(r'Item\s+\[\d+\]\s+causing\s+search\s+overtime:\s*"(?P<item_name>[^"]+)"'),
        'hard_to_place': re.compile(r'Item\s+\[\d+\]\s+is\s+hard\s+to\s+place,\s+performance\s+drops:\s*"(?P<item_name>[^"]+)"'),
        'script_error': re.compile(r'Script\s+(?P<level>Error|Warning):\s*(?P<msg>.*)'),
        'player_connect': re.compile(r'(?P<time>[\d:]+)\s+Player\s+"(?P<name>[^"]+)"\s+\(id=(?P<id>[^)]+)\)\s+connected'),
        'player_disconnect': re.compile(r'(?P<time>[\d:]+)\s+Player\s+"(?P<name>[^"]+)"\s+\(id=(?P<id>[^)]+)\s+pos=<(?P<pos>[^>]+)>\)\s+disconnected'),
    }

    def __init__(self, base_date: datetime = None):
        self.base_date = base_date or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    def parse_line(self, line: str) -> Optional[RPTEvent]:
        # RPT lines usually start with 12:34:56
        ts_match = re.match(r'^(?P<time>[\d:]{8})', line)
        timestamp = self.base_date
        if ts_match:
            try:
                t = datetime.strptime(ts_match.group('time'), "%H:%M:%S").time()
                timestamp = datetime.combine(self.base_date.date(), t)
            except:
                pass

        for event_type, pattern in self.PATTERNS.items():
            match = pattern.search(line)
            if not match: continue
            
            data = match.groupdict()
            return RPTEvent(
                timestamp=timestamp,
                event_type=event_type,
                message=line.strip(),
                data=data
            )
        return None
