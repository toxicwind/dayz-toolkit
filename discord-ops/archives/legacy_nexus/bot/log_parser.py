from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

# Regex Patterns extracted from DayZ-Python-Scripts-And-Tools
PATTERNS = {
    # --- Connection/Disconnection Events ---
    'connection': re.compile(r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\)\s*is connected'),
    'disconnection': re.compile(r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\)\s*has been disconnected'),
    
    # --- Player Status ---
    'unconscious': re.compile(r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\s*pos=<(?P<x>[0-9.-]+),\s*(?P<y>[0-9.-]+),\s*(?P<z>[0-9.-]+)>\)\s*is unconscious'),
    'conscious': re.compile(r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\s*pos=<(?P<x>[0-9.-]+),\s*(?P<y>[0-9.-]+),\s*(?P<z>[0-9.-]+)>\)\s*regained consciousness'),
    'suicide': re.compile(r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*(?:\(DEAD\)\s*)?\(id=(?P<player_id>[A-Fa-f0-9-]+)(?:\s*pos=<(?P<x>[0-9.-]+),\s*(?P<y>[0-9.-]+),\s*(?P<z>[0-9.-]+)>)?\)\s*committed suicide'),
    'respawn': re.compile(r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(DEAD\)\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\s*pos=<(?P<x>[0-9.-]+),\s*(?P<y>[0-9.-]+),\s*(?P<z>[0-9.-]+)>\)\s*is choosing to respawn'),
    
    # --- Combat Events ---
    'hit': re.compile(r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<victim_name>[^"]+?)"\s*(?:\(DEAD\)\s*)?\(id=(?P<victim_id>[A-Fa-f0-9-]+)\s*pos=<(?P<victim_x>[0-9.-]+),\s*(?P<victim_y>[0-9.-]+),\s*(?P<victim_z>[0-9.-]+)>\)\s*\[HP:\s*(?P<victim_hp>[0-9.]+)?\]\s*hit by Player\s*"(?P<attacker_name>[^"]+?)"\s*\(id=(?P<attacker_id>[A-Fa-f0-9-]+)\s*pos=<(?P<attacker_x>[0-9.-]+),\s*(?P<attacker_y>[0-9.-]+),\s*(?P<attacker_z>[0-9.-]+)>\)\s*into\s*(?P<hit_location>[^(]+)\((?P<hit_location_id>\d+)\)\s*for\s*(?P<damage>[0-9.]+)\s+damage\s*\((?P<ammo>[^)]+)\)(?:\s*with\s+(?P<weapon>[^\s]+)(?:\s+from\s+(?P<distance>[0-9.]+)\s+meters)?)?'),
    'kill': re.compile(r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<victim_name>[^"]+?)"\s*\(DEAD\)\s*\(id=(?P<victim_id>[A-Fa-f0-9-]+)\s*pos=<(?P<victim_x>[0-9.-]+),\s*(?P<victim_y>[0-9.-]+),\s*(?P<victim_z>[0-9.-]+)>\)\s*killed by Player\s*"(?P<attacker_name>[^"]+?)"\s*\(id=(?P<attacker_id>[A-Fa-f0-9-]+)\s*pos=<(?P<attacker_x>[0-9.-]+),\s*(?P<attacker_y>[0-9.-]+),\s*(?P<attacker_z>[0-9.-]+)>\)\s*with\s*(?P<weapon>[^\s]+)\s*from\s*(?P<distance>[0-9.]+)\s+meters'),
    'env_hit': re.compile(r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\s*pos=<(?P<x>[0-9.-]+),\s*(?P<y>[0-9.-]+),\s*(?P<z>[0-9.-]+)>\)\s*\[HP:\s*(?P<hp>[0-9.]+)?\]\s+hit by\s+(?P<attacker>[^\s]+)\s+with\s+(?P<weapon>[^\s]+)'),
    
    # --- Building ---
    'placed': re.compile(r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\s*pos=<(?P<x>[0-9.-]+),\s*(?P<y>[0-9.-]+),\s*(?P<z>[0-9.-]+)>\)\s+placed\s+(?P<structure>.+)'),
    'built': re.compile(r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\s*pos=<(?P<x>[0-9.-]+),\s*(?P<y>[0-9.-]+),\s*(?P<z>[0-9.-]+)>\)\s*(?P<action>Built|Dismantled)\s+(?P<structure>[^\s]+)\s+(?P<on_or_from>on|from)\s+(?P<parent>[^\s]+)\s+with\s+(?P<tool>[^\s]+)$'),
    
    # --- Chat (Generic Fallback) ---
    'chat': re.compile(r'(?P<time>\d{2}:\d{2}:\d{2})\s*\|\s*Player\s*"(?P<player_name>[^"]+?)"\s*\(id=(?P<player_id>[A-Fa-f0-9-]+)\)\s*:\s*(?P<message>.+)'),
}

@dataclass
class LogEvent:
    type: str
    timestamp: str 
    raw: str
    data: Dict[str, Any]

class DayZLogParser:
    def parse_line(self, line: str) -> Optional[LogEvent]:
        line = line.strip()
        if not line: return None
        
        for event_type, pattern in PATTERNS.items():
            match = pattern.match(line)
            if match:
                data = match.groupdict()
                # Clean up numeric fields
                for k, v in data.items():
                    if k in ['x', 'y', 'z', 'damage', 'hp', 'distance', 'victim_hp']:
                        try:
                            data[k] = float(v) if v else 0.0
                        except:
                            pass
                
                return LogEvent(
                    type=event_type,
                    timestamp=data.get('time', ''),
                    raw=line,
                    data=data
                )
        
        # Unknown/Generic Line
        return LogEvent(
            type="unknown",
            timestamp="",
            raw=line,
            data={}
        )
