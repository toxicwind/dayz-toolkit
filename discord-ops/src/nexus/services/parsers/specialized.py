import re
from .base import DayZLogParser, LogEvent

class ADMLogParser(DayZLogParser):
    def parse_line(self, line: str) -> LogEvent:
        # Specialized ADM logic (Connect, Disconnect, etc)
        event = super().parse_line(line)
        event.level = "adm"
        if "killed by" in line:
            event.level = "combat"
        return event

class RPTLogParser(DayZLogParser):
    def parse_line(self, line: str) -> LogEvent:
        # Specialized RPT logic (FPS, Memory, etc)
        event = super().parse_line(line)
        event.level = "rpt"
        return event
