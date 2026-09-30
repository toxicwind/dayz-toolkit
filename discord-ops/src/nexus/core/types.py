from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

class LogType(Enum):
    ADM = "adm"
    RPT = "rpt"
    SCRIPT = "script"
    COMBAT = "combat"
    UNKNOWN = "unknown"

class ActivityType(Enum):
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    CHAT = "chat"
    KILL = "kill"
    HIT = "hit"
    ECONOMY = "economy"
    EVENT = "event"

class CombatEventType(Enum):
    KILL = "kill"
    DEATH = "death"
    HIT = "hit"
    FALL = "fall"
    SUICIDE = "suicide"
    ZOMBIE = "zombie"
    ANIMAL = "animal"
    EXPLOSION = "explosion"

@dataclass
class PlayerIdentity:
    name: str
    id: Optional[str] = None
    guid: Optional[str] = None
    pos: Optional[str] = None

@dataclass
class LogEntry:
    timestamp: datetime
    log_type: LogType
    message: str
    activity_type: ActivityType = ActivityType.CHAT
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_line: str = ""
    
    @property
    def raw(self) -> str: return self.raw_line
    @property
    def data(self) -> Dict[str, Any]: return self.metadata

@dataclass
class CombatEvent:
    timestamp: str
    event_type: CombatEventType
    victim_name: str
    victim_id: Optional[str] = None
    victim_pos: Optional[str] = None
    killer_name: Optional[str] = None
    killer_id: Optional[str] = None
    killer_pos: Optional[str] = None
    weapon: Optional[str] = None
    distance: Optional[float] = None
    raw: str = ""
    poi: Optional[str] = None
