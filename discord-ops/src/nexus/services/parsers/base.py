from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

@dataclass
class LogEvent:
    timestamp: str
    source: str
    level: str
    message: str
    raw: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

class DayZLogParser:
    def parse_line(self, line: str) -> Optional[LogEvent]:
        # Basic parser for restoration
        if not line or len(line) < 20: return None
        return LogEvent(
            timestamp=line[:19],
            source="unknown",
            level="info",
            message=line,
            raw=line
        )
